// Audio recording functionality using Web Audio API
class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.recording = false;
        this.audioContext = null;
        this.analyser = null;
        this.canvas = document.getElementById('audioVisualizer');
        this.canvasCtx = this.canvas.getContext('2d');
        this.animationId = null;
        this.recordingInterval = null;
        this.recordingStartTime = 0;
        this.timerElement = document.getElementById('recordingTimer');
        this.recordButton = document.getElementById('recordButton');
        this.audioPlayer = document.getElementById('audioPlayer');
        this.audioPlayerCard = document.getElementById('audioPlayerCard');
        this.transcribeButton = document.getElementById('transcribeButton');
        this.audioUpload = document.getElementById('audioUpload');
        this.clearUpload = document.getElementById('clearUpload');
        this.uploadInfo = document.getElementById('uploadInfo');
        this.fileName = document.getElementById('fileName');
        this.fileSize = document.getElementById('fileSize');
        
        // AI Analysis Elements
        this.transcriptionResults = document.getElementById('transcriptionResults');
        this.transcriptionText = document.getElementById('transcriptionText');
        this.transcriptionStatus = document.getElementById('transcriptionStatus');
        this.caseTypeBadge = document.getElementById('caseTypeBadge');
        this.confidenceMeter = document.getElementById('confidenceMeter');
        this.confidenceText = document.getElementById('confidenceText');
        this.caseTypeEvidence = document.getElementById('caseTypeEvidence');
        this.keyEntities = document.getElementById('keyEntities');
        this.sentimentLabel = document.getElementById('sentimentLabel');
        this.sentimentConfidence = document.getElementById('sentimentConfidence');
        this.sentimentMeter = document.getElementById('sentimentMeter');
        this.sentimentFace = document.querySelector('.sentiment-face');
        this.createCaseBtn = document.getElementById('createCaseBtn');
        this.viewFullAnalysis = document.getElementById('viewFullAnalysis');
        this.caseCreatedAlert = document.getElementById('caseCreatedAlert');
        this.viewCaseLink = document.getElementById('viewCaseLink');
        this.transcribingSpinner = document.getElementById('transcribingSpinner');
        
        this.initializeEventListeners();
    }

    // Initialize event listeners
    initializeEventListeners() {
        // Record button
        this.recordButton.addEventListener('click', () => this.toggleRecording());
        
        // Transcribe button
        this.transcribeButton.addEventListener('click', () => this.handleTranscribe());
        
        // Audio upload
        this.audioUpload.addEventListener('change', (e) => this.handleFileUpload(e));
        this.clearUpload.addEventListener('click', () => this.clearFileUpload());
        
        // Create case button
        if (this.createCaseBtn) {
            this.createCaseBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.createCaseFromAnalysis();
            });
        }
        
        // View full analysis
        if (this.viewFullAnalysis) {
            this.viewFullAnalysis.addEventListener('click', (e) => {
                e.preventDefault();
                // In a real app, this would show a modal or navigate to a detailed view
                this.showToast('Showing detailed analysis', 'info');
            });
        }
        
        // Window resize for canvas
        window.addEventListener('resize', () => this.resizeCanvas());
    }
    
    // Create a new case from the analysis
    async createCaseFromAnalysis() {
        if (!this.transcriptionText.textContent) {
            this.showToast('No transcription available to create a case', 'error');
            return;
        }
        
        try {
            this.createCaseBtn.disabled = true;
            this.createCaseBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Creating Case...';
            
            // In a real app, you would send this to your backend to create a case
            // For now, we'll simulate a successful case creation
            setTimeout(() => {
                this.showToast('Case created successfully!', 'success');
                this.caseCreatedAlert.classList.remove('d-none');
                this.createCaseBtn.innerHTML = '<i class="fas fa-check me-1"></i> Case Created';
                
                // In a real app, you would get the case ID from the response
                const caseId = Math.floor(Math.random() * 1000);
                this.viewCaseLink.href = `/cases/${caseId}`;
                
            }, 1500);
            
        } catch (error) {
            console.error('Error creating case:', error);
            this.showToast('Failed to create case', 'error');
            this.createCaseBtn.disabled = false;
            this.createCaseBtn.innerHTML = '<i class="fas fa-folder-plus me-1"></i> Create Case';
        }
    }

    // Request microphone access and start recording
    async start() {
        if (this.recording) {
            throw new Error('Recording is already in progress');
        }

        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(this.stream);
            this.audioChunks = [];
            this.recordingStartTime = Date.now();

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onerror = (event) => {
                console.error('Recording error:', event.error);
                this.cleanup();
                if (typeof this.onError === 'function') this.onError(event.error);
            };

            this.mediaRecorder.start();
            this.recording = true;

            if (typeof this.onStart === 'function') this.onStart();

            return true;
        } catch (error) {
            console.error('Error accessing microphone:', error);
            throw new Error('Could not access microphone. Please grant microphone permissions.');
        }
    }

    // Stop recording and return the audio blob
    stop() {
        if (!this.recording && !this.isRecording) {
            throw new Error('No active recording to stop');
        }

        return new Promise((resolve, reject) => {
            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                this.cleanup();
                if (typeof this.onStop === 'function') this.onStop(audioBlob);
                resolve(audioBlob);
            };

            this.mediaRecorder.onerror = (event) => {
                this.cleanup();
                const err = new Error('Error during recording');
                if (typeof this.onError === 'function') this.onError(err);
                reject(err);
            };

            this.mediaRecorder.stop();
            this.recording = false;
            this.isRecording = false;
        });
    }

    // Clean up resources
    cleanup() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.startTime = null;
    }

    // Get the current recording duration in seconds
    getRecordingTime() {
        if (!this.isRecording || !this.startTime) return 0;
        return (Date.now() - this.startTime) / 1000;
    }
}

// Export for Node/CommonJS environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioRecorder;
}
