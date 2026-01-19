package com.ert.signalmapper

import android.Manifest
import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : Activity() {

    private lateinit var tvStatus: TextView
    private lateinit var btnStart: Button
    private lateinit var btnShare: Button

    // Receiver to get updates from the Service
    private val uiReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            val text = intent?.getStringExtra(SignalService.EXTRA_LOG_TEXT)
            if (text != null) {
                tvStatus.text = text
                // Update button color based on running state
                if (text.contains("REC TIME")) {
                    btnStart.text = "STOP RECORDING"
                    btnStart.setBackgroundColor(0xFF00FF00.toInt()) // Green
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        tvStatus = findViewById(R.id.tvStatus)
        btnStart = findViewById(R.id.btnStartStop)
        btnShare = findViewById(R.id.btnShare)

        tvStatus.text = "Ready. Press Start."

        // Ask for permissions immediately on launch
        checkAndRequestPermissions()

        btnStart.setOnClickListener {
            tvStatus.text = "Button Clicked... Checking permissions..."

            if (!hasPermissions()) {
                tvStatus.text = "ERROR: Permissions missing! Check Settings."
                Toast.makeText(this, "Grant Permissions first!", Toast.LENGTH_SHORT).show()
                checkAndRequestPermissions()
                return@setOnClickListener
            }

            if (!SignalService.IS_RUNNING) {
                startSignalService()
            } else {
                stopSignalService()
            }
        }

        btnShare.setOnClickListener {
            Toast.makeText(this, "Check 'Documents/SignalMapper' folder", Toast.LENGTH_LONG).show()
        }
    }

    private fun startSignalService() {
        try {
            tvStatus.text = "Attempting to start service..."
            val intent = Intent(this, SignalService::class.java)

            if (Build.VERSION.SDK_INT >= 26) {
                startForegroundService(intent)
            } else {
                startService(intent)
            }
            Toast.makeText(this, "Starting...", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            tvStatus.text = "CRITICAL ERROR: ${e.message}"
            e.printStackTrace()
        }
    }

    private fun stopSignalService() {
        try {
            val intent = Intent(this, SignalService::class.java)
            intent.action = "STOP"
            startService(intent)
            btnStart.text = "START RECORDING"
            btnStart.setBackgroundColor(0xFFFF0000.toInt()) // Red
            tvStatus.text = "Stopping..."
        } catch (e: Exception) {
            tvStatus.text = "Error stopping: ${e.message}"
        }
    }

    private fun hasPermissions(): Boolean {
        val fineLoc = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val phoneState = ContextCompat.checkSelfPermission(this, Manifest.permission.READ_PHONE_STATE) == PackageManager.PERMISSION_GRANTED
        return fineLoc && phoneState
    }

    private fun checkAndRequestPermissions() {
        val permissions = mutableListOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
            Manifest.permission.READ_PHONE_STATE
        )

        if (Build.VERSION.SDK_INT >= 28) {
            permissions.add(Manifest.permission.FOREGROUND_SERVICE)
        }
        // Android 13+ Notification permission
        if (Build.VERSION.SDK_INT >= 33) {
            permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        // Android 14+ Foreground Location permission
        if (Build.VERSION.SDK_INT >= 34) {
            permissions.add("android.permission.FOREGROUND_SERVICE_LOCATION")
        }

        ActivityCompat.requestPermissions(this, permissions.toTypedArray(), 1)
    }

    override fun onResume() {
        super.onResume()
        val filter = IntentFilter(SignalService.ACTION_UPDATE_UI)
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(uiReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(uiReceiver, filter)
        }
    }

    override fun onPause() {
        super.onPause()
        try { unregisterReceiver(uiReceiver) } catch (e: Exception) {}
    }
}