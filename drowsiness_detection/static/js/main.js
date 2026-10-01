document.addEventListener('DOMContentLoaded', () => {
    const valPerclos = document.getElementById('val-perclos');
    const barPerclos = document.getElementById('bar-perclos');
    const valEar = document.getElementById('val-ear');
    const barEar = document.getElementById('bar-ear');
    const valMar = document.getElementById('val-mar');
    const barMar = document.getElementById('bar-mar');
    const valPitch = document.getElementById('val-pitch');
    const valYaw = document.getElementById('val-yaw');
    const mainStatusText = document.getElementById('main-status-text');
    const statusDesc = document.getElementById('status-desc');
    const mainStatusIcon = document.getElementById('main-status-icon');
    const alertBanner = document.getElementById('alert-banner');
    const alertText = document.getElementById('alert-text');
    const calibrationOverlay = document.getElementById('calibration-overlay');
    const calibProgress = document.getElementById('calib-progress');
    const btnToggle = document.getElementById('btn-toggle');
    const btnCalibrate = document.getElementById('btn-calibrate');
    const connectionDot = document.getElementById('connection-dot');

    const pausedOverlay = document.getElementById('paused-overlay');

    let isRunning = true;

    async function updateStatus() {
        if (!isRunning) return; // Stop polling UI if not running
        try {
            const response = await fetch('/status');
            const data = await response.json();

            // Update Metrics
            valPerclos.textContent = `${(data.perclos * 100).toFixed(1)}%`;
            barPerclos.style.width = `${Math.min(data.perclos * 100, 100)}%`;
            
            valEar.textContent = data.ear.toFixed(3);
            barEar.style.width = `${Math.min((data.ear / 0.4) * 100, 100)}%`;

            valMar.textContent = data.mar.toFixed(3);
            barMar.style.width = `${Math.min((data.mar / 0.8) * 100, 100)}%`;

            valPitch.textContent = data.pitch ? `${data.pitch.toFixed(1)}°` : 'N/A';
            valYaw.textContent = data.yaw ? `${data.yaw.toFixed(1)}°` : 'N/A';

            // Calibration Logic
            if (data.calibrating) {
                calibrationOverlay.classList.remove('hidden');
                calibProgress.textContent = `${data.calibration_progress}%`;
            } else {
                calibrationOverlay.classList.add('hidden');
            }

            // Status Logic
            if (data.status === "Drowsy") {
                mainStatusText.textContent = "Drowsiness Alert";
                mainStatusText.style.color = "var(--danger)";
                statusDesc.textContent = data.alert_message;
                mainStatusIcon.innerHTML = '<i class="fas fa-exclamation-circle"></i>';
                mainStatusIcon.style.color = "var(--danger)";
                alertBanner.classList.remove('hidden');
                alertText.textContent = data.alert_message;
            } else if (data.status === "No Face Detected") {
                mainStatusText.textContent = "No Driver Detected";
                mainStatusText.style.color = "var(--text-muted)";
                statusDesc.textContent = "Please ensure face is visible to camera.";
                mainStatusIcon.innerHTML = '<i class="fas fa-user-slash"></i>';
                mainStatusIcon.style.color = "var(--text-muted)";
                alertBanner.classList.add('hidden');
            } else {
                mainStatusText.textContent = "Active Monitoring";
                mainStatusText.style.color = "var(--success)";
                statusDesc.textContent = data.is_dark ? "Night Vision Active" : "Scanning for fatigue patterns.";
                mainStatusIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
                mainStatusIcon.style.color = "var(--success)";
                alertBanner.classList.add('hidden');
            }

            connectionDot.style.backgroundColor = "var(--success)";
            connectionDot.style.boxShadow = "0 0 10px var(--success)";

        } catch (error) {
            console.error("Error fetching status:", error);
            connectionDot.style.backgroundColor = "var(--danger)";
            connectionDot.style.boxShadow = "0 0 10px var(--danger)";
        }
    }

    // Controls
    btnToggle.addEventListener('click', async () => {
        if (isRunning) {
            await fetch('/stop');
            btnToggle.textContent = "Start Monitoring";
            btnToggle.classList.remove('btn-primary');
            btnToggle.classList.add('btn-secondary');
            document.body.classList.add('monitoring-stopped');
            pausedOverlay.classList.remove('hidden');
            
            // Update Status Card UI
            mainStatusText.textContent = "Monitoring Paused";
            mainStatusText.style.color = "var(--text-muted)";
            statusDesc.textContent = "System is idle. Click Start to resume protection.";
            mainStatusIcon.innerHTML = '<i class="fas fa-pause-circle"></i>';
            mainStatusIcon.style.color = "var(--text-muted)";
            mainStatusIcon.classList.remove('active');
            alertBanner.classList.add('hidden');
            
            isRunning = false;
        } else {
            await fetch('/start');
            btnToggle.textContent = "Stop Monitoring";
            btnToggle.classList.remove('btn-secondary');
            btnToggle.classList.add('btn-primary');
            document.body.classList.remove('monitoring-stopped');
            pausedOverlay.classList.add('hidden');
            mainStatusIcon.classList.add('active');
            isRunning = true;
        }
    });

    btnCalibrate.addEventListener('click', async () => {
        // Ensure system is running first
        if (!isRunning) {
            await fetch('/start');
            isRunning = true;
            btnToggle.textContent = "Stop Monitoring";
            btnToggle.classList.remove('btn-secondary');
            btnToggle.classList.add('btn-primary');
            document.body.classList.remove('monitoring-stopped');
            pausedOverlay.classList.add('hidden');
        }
        
        // Trigger re-calibration route
        await fetch('/calibrate');
        calibrationOverlay.classList.remove('hidden');
        calibProgress.textContent = "0%";
    });

    // Start polling
    setInterval(updateStatus, 200);
});
