package com.ert.signalmapper

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.location.Location
import android.os.Build
import android.os.Environment
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.telephony.*
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import com.google.android.gms.location.*
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.*

class SignalService : Service() {

    companion object {
        const val ACTION_UPDATE_UI = "com.ert.signalmapper.UPDATE_UI"
        const val EXTRA_LOG_TEXT = "log_text"
        var IS_RUNNING = false
    }

    private lateinit var subscriptionManager: SubscriptionManager
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private lateinit var locationCallback: LocationCallback
    private var latestLocation: Location? = null

    private var fileWriter: FileWriter? = null
    private var startTime = 0L
    private val handler = Handler(Looper.getMainLooper())
    private var wakeLock: PowerManager.WakeLock? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        try {
            subscriptionManager = getSystemService(Context.TELEPHONY_SUBSCRIPTION_SERVICE) as SubscriptionManager
            fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)

            val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
            wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "SignalMapper::RecordingLock")
            try { wakeLock?.acquire(10*60*60*1000L) } catch (e: Exception) {}

            locationCallback = object : LocationCallback() {
                override fun onLocationResult(locationResult: LocationResult) {
                    locationResult.lastLocation?.let { latestLocation = it }
                }
            }
        } catch (e: Exception) {
            broadcastUpdate("Startup Error: ${e.message}")
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "STOP") {
            stopRecording()
            return START_NOT_STICKY
        }

        if (!IS_RUNNING) {
            try {
                IS_RUNNING = true
                startTime = System.currentTimeMillis()

                // CRITICAL: Start Foreground IMMEDIATELY to prevent Android killing the app
                startForegroundServiceNotification()

                broadcastUpdate("Service Started. Waiting for GPS...")
                startGPS()
                setupFile()
                recordLoop.run()
            } catch (e: Exception) {
                IS_RUNNING = false
                broadcastUpdate("CRASH: ${e.message}")
                e.printStackTrace()
                stopSelf()
            }
        }

        return START_STICKY
    }

    private fun startForegroundServiceNotification() {
        val channelId = "SignalLogChannel"
        val channel = NotificationChannel(channelId, "Signal Logging", NotificationManager.IMPORTANCE_LOW)
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)

        val pendingIntent = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val notification = NotificationCompat.Builder(this, channelId)
            .setContentTitle("Signal Mapper Recording")
            .setContentText("Do not kill this app.")
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()

        // Android 14 Requirement fix
        if (Build.VERSION.SDK_INT >= 34) {
            try {
                startForeground(1, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION)
            } catch (e: Exception) {
                // Fallback if specific permission is missing
                startForeground(1, notification)
            }
        } else {
            startForeground(1, notification)
        }
    }

    private fun setupFile() {
        val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
        val fileName = "Signal_Log_Advanced_$timeStamp.csv"
        val path = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS)
        val folder = File(path, "SignalMapper")
        if (!folder.exists()) folder.mkdirs()
        val file = File(folder, fileName)

        try {
            fileWriter = FileWriter(file)
            fileWriter?.append("Timestamp,Latitude,Longitude,Altitude,Speed,Operator,Slot,NetworkType,PCI,RSRP,RSRQ,SNR\n")
        } catch (e: Exception) {
            broadcastUpdate("File Error: ${e.message}")
        }
    }

    private fun startGPS() {
        if (ActivityCompat.checkSelfPermission(this, android.Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
            val locationRequest = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 1000)
                .setMinUpdateIntervalMillis(500)
                .build()
            fusedLocationClient.requestLocationUpdates(locationRequest, locationCallback, Looper.getMainLooper())
        } else {
            broadcastUpdate("GPS Permission Missing!")
        }
    }

    private val recordLoop = object : Runnable {
        override fun run() {
            if (!IS_RUNNING) return
            scanAllSims()
            handler.postDelayed(this, 1000)
        }
    }

    private fun scanAllSims() {
        if (ActivityCompat.checkSelfPermission(this, android.Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
            broadcastUpdate("Phone Permission Missing!")
            return
        }

        val activeSubs = subscriptionManager.activeSubscriptionInfoList ?: emptyList()
        val location = latestLocation

        val millis = System.currentTimeMillis() - startTime
        val seconds = (millis / 1000) % 60
        val minutes = (millis / (1000 * 60)) % 60
        val hours = (millis / (1000 * 60 * 60))
        val duration = String.format("%02d:%02d:%02d", hours, minutes, seconds)

        var logBuffer = "REC TIME: $duration\n"

        if (location != null) {
            val time = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
            logBuffer += "GPS: OK | Spd: ${location.speed.toInt()} m/s\n"

            if (activeSubs.isEmpty()) {
                logBuffer += "No SIM Cards detected.\n"
            }

            for (subInfo in activeSubs) {
                val carrier = subInfo.carrierName.toString()
                val slot = subInfo.simSlotIndex + 1
                logBuffer += "SIM $slot: $carrier\n"

                val tm = getSystemService(TelephonyManager::class.java).createForSubscriptionId(subInfo.subscriptionId)
                tm.requestCellInfoUpdate(mainExecutor, object : TelephonyManager.CellInfoCallback() {
                    override fun onCellInfo(cellInfoList: MutableList<CellInfo>) {
                        processData(cellInfoList, location, time, slot, carrier)
                    }
                    override fun onError(errorCode: Int, detail: Throwable?) {
                        processData(tm.allCellInfo, location, time, slot, carrier)
                    }
                })
            }
        } else {
            logBuffer += "Waiting for GPS Fix... (Go Outside)\n"
        }

        broadcastUpdate(logBuffer)
    }

    private fun broadcastUpdate(text: String) {
        val intent = Intent(ACTION_UPDATE_UI)
        intent.putExtra(EXTRA_LOG_TEXT, text)
        intent.setPackage(packageName) // IMPORTANT: Ensures the activity receives it
        sendBroadcast(intent)
    }

    private fun processData(cellInfos: List<CellInfo>?, location: Location, time: String, slot: Int, carrierName: String) {
        if (cellInfos == null) return
        var foundSignal = false

        for (cell in cellInfos) {
            if (cell.isRegistered) {
                var type = "Unknown"; var rsrp = -140; var snr = -20; var rsrq = -20; var pci = 0
                try {
                    if (cell is CellInfoLte) {
                        type = "LTE"
                        rsrp = cell.cellSignalStrength.rsrp
                        snr = cell.cellSignalStrength.rssnr
                        rsrq = cell.cellSignalStrength.rsrq
                        pci = cell.cellIdentity.pci
                    } else if (Build.VERSION.SDK_INT >= 29 && cell is CellInfoNr) {
                        type = "5G"
                        val s = cell.cellSignalStrength as CellSignalStrengthNr
                        rsrp = s.ssRsrp; snr = s.ssSinr; rsrq = s.ssRsrq
                        val identity = cell.cellIdentity
                        if (identity is CellIdentityNr) pci = identity.pci
                    } else if (cell is CellInfoWcdma) {
                        type = "3G"
                        rsrp = cell.cellSignalStrength.dbm
                        pci = cell.cellIdentity.psc
                    } else if (cell is CellInfoGsm) {
                        type = "2G"
                        rsrp = cell.cellSignalStrength.dbm
                        pci = cell.cellIdentity.cid
                    }

                    if (type != "Unknown") {
                        if (rsrp > -40) rsrp = -140
                        val row = "$time,${location.latitude},${location.longitude},${location.altitude},${location.speed},${carrierName},SIM$slot,${type},${pci},${rsrp},${rsrq},${snr}\n"
                        fileWriter?.append(row)
                        foundSignal = true
                    }
                } catch (e: Exception) { }
            }
        }
        if (!foundSignal) {
            try { fileWriter?.append("$time,${location.latitude},${location.longitude},${location.altitude},${location.speed},${carrierName},SIM$slot,NO_SIGNAL,0,-140,-20,-20\n") } catch (e:Exception){}
        }
    }

    private fun stopRecording() {
        IS_RUNNING = false
        handler.removeCallbacks(recordLoop)
        fusedLocationClient.removeLocationUpdates(locationCallback)

        try {
            fileWriter?.flush()
            fileWriter?.close()
        } catch (e: Exception) {}

        try { wakeLock?.release() } catch (e: Exception){}

        if (Build.VERSION.SDK_INT >= 24) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            stopForeground(true)
        }
        stopSelf()

        broadcastUpdate("Recording Stopped.\nFile Saved in Documents/SignalMapper")
    }
}