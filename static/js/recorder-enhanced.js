// Enhanced Audio Recorder with Visualization and Playback
class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
        this.startTime = null;
        this.visualizer = null;
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;
        this.animationId = null;
        this.transcriptionId = null;
        this.transcriptionCheckInterval = null;
        
        // UI Elements
        this.recordButton = document.getElementById('recordButton');
        this.visualizerCanvas = document.getElementById('audioVisualizer');
        this.timerDisplay = document.querySelector('#recordingTimer span');
        this.recordingStatus = document.getElementById('recordingStatus');
        this.volumeMeter = document.getElementById('volumeMeter');
        this.transcriptionOutput = document.getElementById('transcriptionOutput');
        this.transcribeButton = document.getElementById('transcribeBtn');
        this.audioPlayer = document.getElementById('audioPlayback');
        
        // Initialize
        this.initEventListeners();
        this.setupCanvas();
    }

    setupCanvas() {
        // Set canvas dimensions
        const dpr = window.devicePixelRatio || 1;
        this.visualizerCanvas.width = this.visualizerCanvas.offsetWidth * dpr;
        this.visualizerCanvas.height = 100 * dpr;
        this.visualizerCanvas.style.width = '100%';
        this.visualizerCanvas.style.height = '100px';
    }

    initEventListeners() {
        if (this.recordButton) {
            this.recordButton.addEventListener('click', () => {
                if (this.isRecording) {
                    this.stop();
                } else {
                    this.start();
                }
            });
        }
        
        // Handle window resize
        window.addEventListener('resize', () => this.setupCanvas());
    }

    async start() {
        if (this.isRecording) return;
        
        // Show toast notification
        this.showToast('info', 'Preparing', 'Getting ready to record...');
        
        // Update button state
        this.recordButton.classList.add('recording');
        this.recordButton.innerHTML = '<i class="fas fa-stop"></i>';
        this.recordButton.title = 'Click to stop recording';
        try {
            this.audioChunks = [];
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(this.stream);
            
            // Setup audio context for visualization
            this.setupAudioContext();
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                const audioUrl = URL.createObjectURL(audioBlob);
                this.audioPlayer.src = audioUrl;
                
                // Enable the transcribe button
                this.transcribeButton.disabled = false;
                this.transcribeButton.onclick = () => this.transcribeAudio(audioBlob);
                
                // Show the audio player
                document.getElementById('audioPlayerCard').classList.remove('d-none');
                
                // Stop all tracks in the stream
                this.stream.getTracks().forEach(track => track.stop());
                
                // Reset visualization
                if (this.animationId) {
                    cancelAnimationFrame(this.animationId);
                    this.animationId = null;
                }
                
                this.showToast('success', 'Recording Complete', 'Your recording is ready for transcription');
            };
            
            this.mediaRecorder.start(100); // Collect data every 100ms
            this.isRecording = true;
            this.startTime = Date.now();
            
            // Update UI
            this.recordButton.disabled = true;
            this.stopButton.disabled = false;
            document.getElementById('recordingTimer').classList.remove('d-none');
            this.recordButton.classList.add('recording');
            
            // Start timer
            this.updateTimer();
            
            // Start visualization
            this.drawVisualizer();
            
            this.showToast('success', 'Recording', 'Recording started...');
            
        } catch (error) {
            console.error('Error accessing microphone:', error);
            this.showToast('error', 'Error', 'Could not access microphone. Please check permissions.');
        }
        if (this.isRecording) return;

        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    channelCount: 1
                } 
            });
            
            this.setupAudioContext();
            this.mediaRecorder = new MediaRecorder(this.stream);
            this.audioChunks = [];
            this.startTime = Date.now();

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onerror = (event) => {
                this.showError('Recording error: ' + (event.error?.message || 'Unknown error'));
                this.cleanup();
            };

            this.mediaRecorder.start(100);
            this.isRecording = true;
            this.updateUIForRecording(true);
            this.updateTimer();
            this.visualize();

        } catch (error) {
            this.showError('Microphone access denied. Please allow microphone access to record.');
            console.error('Error accessing microphone:', error);
        }
    }

    async stop() {
        if (!this.isRecording) return;
        
        this.mediaRecorder.stop();
        this.isRecording = false;
        
        // Update UI
        this.recordButton.classList.remove('recording');
        this.recordButton.innerHTML = '<i class="fas fa-microphone"></i>';
        this.recordButton.title = 'Click to start recording';
        
        // Stop all tracks in the stream
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
        if (!this.isRecording) return;

        return new Promise((resolve) => {
            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                this.cleanup();
                this.updateUIForRecording(false);
                resolve(audioBlob);
            };

            this.mediaRecorder.stop();
            this.isRecording = false;
            cancelAnimationFrame(this.animationId);
            
            // Stop all tracks in the stream
            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
            }
        });
    }

    setupAudioContext() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.analyser = this.audioContext.createAnalyser();
        const source = this.audioContext.createMediaStreamSource(this.stream);
        source.connect(this.analyser);
        this.analyser.fftSize = 256;
        const bufferLength = this.analyser.frequencyBinCount;
        this.dataArray = new Uint8Array(bufferLength);
    }

    visualize() {
        if (!this.isRecording) return;

        this.animationId = requestAnimationFrame(() => this.visualize());
        
        this.analyser.getByteFrequencyData(this.dataArray);
        const canvas = this.visualizerCanvas;
        const canvasCtx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;
        
        canvasCtx.clearRect(0, 0, width, height);
        
        const barWidth = (width / this.dataArray.length) * 2.5;
        let x = 0;
        let total = 0;
        
        for (let i = 0; i < this.dataArray.length; i++) {
            const barHeight = (this.dataArray[i] / 255) * height;
            total += this.dataArray[i];
            
            // Create gradient
            const gradient = canvasCtx.createLinearGradient(0, height - barHeight, 0, height);
            gradient.addColorStop(0, '#4a89dc');
            gradient.addColorStop(1, '#5d9cec');
            
            canvasCtx.fillStyle = gradient;
            canvasCtx.fillRect(x, height - barHeight, barWidth, barHeight);
            
            x += barWidth + 1;
        }
        
        // Update volume meter
        const avg = (total / this.dataArray.length) / 2.55; // Convert to percentage
        if (this.volumeMeter) {
            this.volumeMeter.style.width = `${Math.min(100, avg)}%`;
            this.volumeMeter.setAttribute('aria-valuenow', avg);
            
            // Change color based on volume
            if (avg > 80) {
                this.volumeMeter.className = 'progress-bar bg-danger';
            } else if (avg > 50) {
                this.volumeMeter.className = 'progress-bar bg-warning';
            } else {
                this.volumeMeter.className = 'progress-bar bg-success';
            }
        }
    }

    updateTimer() {
        if (!this.isRecording) return;
        
        const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
        const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
        const seconds = (elapsed % 60).toString().padStart(2, '0');
        
        if (this.timerDisplay) {
            this.timerDisplay.textContent = `${minutes}:${seconds}`;
        }
        
        setTimeout(() => this.updateTimer(), 1000);
    }

    updateUIForRecording(isRecording) {
        if (this.recordButton) {
            this.recordButton.disabled = isRecording;
            this.recordButton.classList.toggle('btn-primary', !isRecording);
            this.recordButton.classList.toggle('btn-outline-secondary', isRecording);
        }
        
        if (this.stopButton) {
            this.stopButton.disabled = !isRecording;
            this.stopButton.classList.toggle('btn-danger', isRecording);
            this.stopButton.classList.toggle('btn-outline-danger', !isRecording);
        }
        
        if (this.visualizerCanvas) {
            this.visualizerCanvas.style.display = isRecording ? 'block' : 'none';
        }
        
        if (this.recordingStatus) {
            this.recordingStatus.textContent = isRecording 
                ? 'Recording in progress...' 
                : 'Click "Start Recording" to begin.';
        }
        
        // Show/hide recording timer
        const timerElement = document.getElementById('recordingTimer');
        if (timerElement) {
            timerElement.classList.toggle('d-none', !isRecording);
        }
    }

    showError(message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger alert-dismissible fade show mt-3';
        alertDiv.innerHTML = `
            <i class="fas fa-exclamation-circle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        const container = document.querySelector('.container.mt-4') || document.body;
        container.prepend(alertDiv);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = bootstrap.Alert.getOrCreateInstance(alertDiv);
            if (alert) alert.close();
        }, 5000);
    }

    cleanup() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close().catch(console.error);
        }
        
        cancelAnimationFrame(this.animationId);
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.startTime = null;
    }

    // Transcribe the recorded audio
    async transcribeAudio(audioBlob) {
        try {
            this.showToast('info', 'Transcribing', 'Processing your recording...');
            this.transcribeButton.disabled = true;
            this.transcribeButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Transcribing...';
            
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.wav');
            
            const response = await fetch('/transcribe', {
                method: 'POST',
                body: formData,
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to start transcription');
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            this.transcriptionId = data.transcript_id;
            this.checkTranscriptionStatus();
            
        } catch (error) {
            console.error('Transcription error:', error);
            this.showToast('error', 'Transcription Error', error.message || 'Failed to transcribe audio');
            this.transcribeButton.disabled = false;
            this.transcribeButton.innerHTML = '<i class="fas fa-play me-1"></i>Transcribe';
        }
    }
    
    // Check transcription status
    async checkTranscriptionStatus() {
        if (!this.transcriptionId) return;
        
        try {
            const response = await fetch(`/transcribe/status/${this.transcriptionId}`);
            const data = await response.json();
            
            if (data.status === 'completed') {
                // Update UI with transcription
                this.transcriptionOutput.innerHTML = `
                    <div class="p-3">
                        <h5>Transcription Result:</h5>
                        <div class="transcription-text p-3 bg-light rounded">
                            ${data.text.replace(/\n/g, '<br>')}
                        </div>
                        <div class="mt-3">
                            <button id="copyTextBtn" class="btn btn-sm btn-outline-primary me-2">
                                <i class="far fa-copy me-1"></i>Copy Text
                            </button>
                            <button id="downloadTextBtn" class="btn btn-sm btn-outline-secondary">
                                <i class="fas fa-download me-1"></i>Download
                            </button>
                        </div>
                    </div>
                `;
                
                // Add event listeners for copy and download
                document.getElementById('copyTextBtn').addEventListener('click', () => {
                    navigator.clipboard.writeText(data.text);
                    this.showToast('success', 'Copied', 'Transcription copied to clipboard');
                });
                
                document.getElementById('downloadTextBtn').addEventListener('click', () => {
                    const blob = new Blob([data.text], { type: 'text/plain' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `transcription-${new Date().toISOString().slice(0, 10)}.txt`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                });
                
                this.showToast('success', 'Transcription Complete', 'Your transcription is ready');
                
            } else if (data.status === 'processing') {
                // Check again after delay
                setTimeout(() => this.checkTranscriptionStatus(), 2000);
                
            } else if (data.status === 'error') {
                throw new Error(data.error || 'Transcription failed');
            }
            
        } catch (error) {
            console.error('Error checking transcription status:', error);
            this.showToast('error', 'Transcription Error', error.message || 'Failed to get transcription status');
        } finally {
            this.transcribeButton.disabled = false;
            this.transcribeButton.innerHTML = '<i class="fas fa-play me-1"></i>Transcribe';
        }
    }
    
    // Helper function to show toast notifications
    showToast(type, title, message) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong><br>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            const container = document.createElement('div');
            container.id = 'toastContainer';
            container.style.position = 'fixed';
            container.style.top = '20px';
            container.style.right = '20px';
            container.style.zIndex = '1100';
            document.body.appendChild(container);
        }
        
        document.getElementById('toastContainer').appendChild(toast);
        
        const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 5000 });
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if we're on a page with the recorder
    if (document.getElementById('audioVisualizer')) {
        window.audioRecorder = new AudioRecorder();
    }
});
