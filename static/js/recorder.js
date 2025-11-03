// Audio recording functionality using Web Audio API
class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.stream = null;
    }

    // Request microphone access and start recording
    async start() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(this.stream);
            this.audioChunks = [];
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.start();
            this.isRecording = true;
            
            return true;
        } catch (error) {
            console.error('Error accessing microphone:', error);
            throw new Error('Could not access microphone. Please ensure you have given microphone permissions.');
        }
    }

    // Stop recording and return the audio blob
    async stop() {
        if (!this.isRecording) {
            throw new Error('No active recording to stop');
        }

        return new Promise((resolve, reject) => {
            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
                this.cleanup();
                resolve(audioBlob);
            };
            
            this.mediaRecorder.onerror = (event) => {
                this.cleanup();
                reject(new Error('Error during recording'));
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
    }

    // Get the current recording time in seconds
    getRecordingTime() {
        if (!this.mediaRecorder || !this.mediaRecorder.startTime) return 0;
        return (Date.now() - this.mediaRecorder.startTime) / 1000;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioRecorder;
}
