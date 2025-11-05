// Audio Player with Playback Controls
class AudioPlayer {
    constructor() {
        this.audio = document.createElement('audio');
        this.playPauseBtn = document.getElementById('playPauseBtn');
        this.progressBar = document.getElementById('progressBar');
        this.progressFill = this.progressBar?.querySelector('.progress-bar');
        this.currentTimeEl = document.getElementById('currentTime');
        this.durationEl = document.getElementById('duration');
        this.playbackSpeed = document.getElementById('playbackSpeed');
        this.volumeControl = document.getElementById('volumeControl');
        this.volumeIcon = document.getElementById('volumeIcon');
        this.isPlaying = false;
        
        this.initEventListeners();
    }

    initEventListeners() {
        if (!this.playPauseBtn) return;

        // Play/Pause button
        this.playPauseBtn.addEventListener('click', () => this.togglePlayback());

        // Progress bar click
        if (this.progressBar) {
            this.progressBar.addEventListener('click', (e) => this.seek(e));
        }

        // Time update
        this.audio.addEventListener('timeupdate', () => this.updateProgress());
        this.audio.addEventListener('loadedmetadata', () => this.updateDuration());
        this.audio.addEventListener('ended', () => this.onPlaybackEnd());
        this.audio.addEventListener('volumechange', () => this.updateVolumeIcon());

        // Playback speed
        if (this.playbackSpeed) {
            this.playbackSpeed.addEventListener('change', (e) => {
                this.audio.playbackRate = parseFloat(e.target.value);
            });
        }

        // Volume control
        if (this.volumeControl) {
            this.volumeControl.addEventListener('input', (e) => {
                this.audio.volume = e.target.value / 100;
                localStorage.setItem('audioVolume', e.target.value);
            });
            
            // Load saved volume
            const savedVolume = localStorage.getItem('audioVolume');
            if (savedVolume !== null) {
                this.audio.volume = savedVolume / 100;
                this.volumeControl.value = savedVolume;
            }
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Space to play/pause (when not in input fields)
            if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
                this.togglePlayback();
            }
            // Left/Right arrow to seek
            else if (e.code === 'ArrowLeft') {
                e.preventDefault();
                this.audio.currentTime = Math.max(0, this.audio.currentTime - 5);
            }
            else if (e.code === 'ArrowRight') {
                e.preventDefault();
                this.audio.currentTime = Math.min(this.audio.duration, this.audio.currentTime + 5);
            }
            // M to mute/unmute
            else if (e.code === 'KeyM') {
                e.preventDefault();
                this.audio.muted = !this.audio.muted;
                this.updateVolumeIcon();
            }
        });
    }

    loadAudio(url) {
        return new Promise((resolve, reject) => {
            this.audio.pause();
            this.audio.src = url;
            this.audio.load();
            
            this.audio.oncanplaythrough = () => {
                resolve();
            };
            
            this.audio.onerror = (e) => {
                console.error('Error loading audio:', e);
                reject(new Error('Failed to load audio'));
            };
        });
    }

    togglePlayback() {
        if (this.audio.paused) {
            this.play();
        } else {
            this.pause();
        }
    }

    play() {
        const playPromise = this.audio.play();
        
        if (playPromise !== undefined) {
            playPromise.catch(error => {
                console.error('Playback failed:', error);
                this.showError('Playback failed. Please try again.');
            });
        }
        
        this.isPlaying = true;
        this.updatePlayButton();
    }

    pause() {
        this.audio.pause();
        this.isPlaying = false;
        this.updatePlayButton();
    }

    seek(e) {
        if (!this.progressBar) return;
        
        const rect = this.progressBar.getBoundingClientRect();
        const pos = (e.clientX - rect.left) / rect.width;
        this.audio.currentTime = pos * this.audio.duration;
    }

    updateProgress() {
        if (!this.progressFill || !this.currentTimeEl) return;
        
        const progress = (this.audio.currentTime / this.audio.duration) * 100;
        this.progressFill.style.width = `${progress}%`;
        this.currentTimeEl.textContent = this.formatTime(this.audio.currentTime);
        
        // Update transcription highlighting if available
        this.updateTranscriptionHighlight();
    }

    updateDuration() {
        if (!this.durationEl) return;
        this.durationEl.textContent = this.formatTime(this.audio.duration);
    }

    updatePlayButton() {
        if (!this.playPauseBtn) return;
        
        if (this.isPlaying) {
            this.playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';
            this.playPauseBtn.setAttribute('aria-label', 'Pause');
        } else {
            this.playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
            this.playPauseBtn.setAttribute('aria-label', 'Play');
        }
    }

    updateVolumeIcon() {
        if (!this.volumeIcon) return;
        
        if (this.audio.muted || this.audio.volume === 0) {
            this.volumeIcon.className = 'fas fa-volume-mute';
        } else if (this.audio.volume < 0.5) {
            this.volumeIcon.className = 'fas fa-volume-down';
        } else {
            this.volumeIcon.className = 'fas fa-volume-up';
        }
    }

    updateTranscriptionHighlight() {
        // This would be implemented to highlight the current word/sentence in the transcription
        // based on the current playback time and word timestamps from the transcription
    }

    onPlaybackEnd() {
        this.isPlaying = false;
        this.updatePlayButton();
        
        // Reset progress bar
        if (this.progressFill) {
            this.progressFill.style.width = '0%';
        }
        
        if (this.currentTimeEl) {
            this.currentTimeEl.textContent = this.formatTime(0);
        }
    }

    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
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
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if we're on a page with the audio player
    if (document.getElementById('playPauseBtn')) {
        window.audioPlayer = new AudioPlayer();
    }
});
