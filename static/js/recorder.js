// Audio recording functionality using Web Audio API
class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
        this.startTime = null;

        // Optional callbacks
        this.onStart = null;
        this.onStop = null;
        this.onError = null;
    }

    // Request microphone access and start recording
    async start() {
        if (this.isRecording) {
            throw new Error('Recording is already in progress');
        }

        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(this.stream);
            this.audioChunks = [];
            this.startTime = Date.now();

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
            this.isRecording = true;

            if (typeof this.onStart === 'function') this.onStart();

            return true;
        } catch (error) {
            console.error('Error accessing microphone:', error);
            throw new Error('Could not access microphone. Please grant microphone permissions.');
        }
    }

    // Stop recording and return the audio blob
    stop() {
        if (!this.isRecording) {
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
