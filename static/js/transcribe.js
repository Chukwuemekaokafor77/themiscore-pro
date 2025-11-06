/**
 * Transcription Interface - Audio Recording and Transcription
 * Handles voice recording, file upload, and transcription polling
 */

// Global state
let mediaRecorder = null;
let audioChunks = [];
let recordingStartTime = null;
let timerInterval = null;
let currentTranscriptId = null;
let currentTranscriptText = '';

// DOM Elements (initialized on load)
let recordButton, recordingTimer, transcriptionOutput, createCaseBtn;
let uploadAudioBtn, audioFileInput, clearTranscriptionBtn, downloadTextBtn;

/**
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    recordButton = document.getElementById('recordButton');
    recordingTimer = document.getElementById('recordingTimer');
    transcriptionOutput = document.getElementById('transcriptionOutput');
    createCaseBtn = document.getElementById('createCaseBtn');
    uploadAudioBtn = document.getElementById('uploadAudioBtn');
    audioFileInput = document.getElementById('audioFileInput');
    clearTranscriptionBtn = document.getElementById('clearTranscriptionBtn');
    downloadTextBtn = document.getElementById('downloadTextBtn');
    
    // Set up event listeners
    if (recordButton) {
        recordButton.addEventListener('click', toggleRecording);
    }
    
    if (uploadAudioBtn && audioFileInput) {
        uploadAudioBtn.addEventListener('click', () => audioFileInput.click());
        audioFileInput.addEventListener('change', handleFileUpload);
    }
    
    if (clearTranscriptionBtn) {
        clearTranscriptionBtn.addEventListener('click', clearTranscription);
    }
    
    if (downloadTextBtn) {
        downloadTextBtn.addEventListener('click', downloadTranscript);
    }
    
    if (createCaseBtn) {
        createCaseBtn.addEventListener('click', showCreateCaseModal);
    }
    
    console.log('Transcription interface initialized');
});

/**
 * Toggle recording on/off
 */
async function toggleRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        stopRecording();
    } else {
        await startRecording();
    }
}

/**
 * Start audio recording
 */
async function startRecording() {
    try {
        // Request microphone access
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });
        
        // Create MediaRecorder
        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
        });
        
        audioChunks = [];
        
        // Handle data available
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        // Handle recording stop
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await uploadAudio(audioBlob);
            
            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
        };
        
        // Start recording
        mediaRecorder.start(1000); // Collect data every second
        recordingStartTime = Date.now();
        
        // Update UI
        updateRecordingUI('recording');
        startTimer();
        
        console.log('Recording started');
        
    } catch (error) {
        console.error('Error starting recording:', error);
        
        let errorMessage = 'Could not access microphone. ';
        if (error.name === 'NotAllowedError') {
            errorMessage += 'Please allow microphone access in your browser settings.';
        } else if (error.name === 'NotFoundError') {
            errorMessage += 'No microphone found. Please connect a microphone.';
        } else {
            errorMessage += error.message;
        }
        
        showAlert(errorMessage, 'danger');
    }
}

/**
 * Stop audio recording
 */
function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        stopTimer();
        updateRecordingUI('stopped');
        console.log('Recording stopped');
    }
}

/**
 * Start recording timer
 */
function startTimer() {
    if (recordingTimer) {
        recordingTimer.classList.remove('d-none');
        
        timerInterval = setInterval(() => {
            const elapsed = Date.now() - recordingStartTime;
            const minutes = Math.floor(elapsed / 60000);
            const seconds = Math.floor((elapsed % 60000) / 1000);
            
            const timerSpan = recordingTimer.querySelector('span');
            if (timerSpan) {
                timerSpan.textContent = 
                    `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
            
            // Auto-stop after 15 minutes
            if (minutes >= 15) {
                stopRecording();
                showAlert('Maximum recording time (15 minutes) reached. Recording stopped.', 'warning');
            }
        }, 1000);
    }
}

/**
 * Stop recording timer
 */
function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    if (recordingTimer) {
        recordingTimer.classList.add('d-none');
    }
}

/**
 * Update recording UI state
 */
function updateRecordingUI(state) {
    if (!recordButton) return;
    
    const icon = recordButton.querySelector('i');
    
    switch(state) {
        case 'recording':
            recordButton.classList.add('recording');
            recordButton.setAttribute('title', 'Stop recording');
            if (icon) {
                icon.className = 'bi bi-stop-fill';
            }
            break;
            
        case 'stopped':
        case 'idle':
            recordButton.classList.remove('recording');
            recordButton.setAttribute('title', 'Start recording');
            if (icon) {
                icon.className = 'bi bi-mic-fill';
            }
            break;
    }
}

/**
 * Upload audio file
 */
async function uploadAudio(audioBlob) {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, `recording_${Date.now()}.webm`);
    
    try {
        showTranscriptionStatus('Uploading audio...');
        
        const response = await fetch('/transcribe', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        if (data.transcript_id) {
            currentTranscriptId = data.transcript_id;
            showTranscriptionStatus('Transcribing audio...');
            pollTranscriptionStatus(data.transcript_id);
        } else {
            throw new Error('No transcript ID received');
        }
        
    } catch (error) {
        console.error('Upload error:', error);
        showAlert('Failed to upload audio: ' + error.message, 'danger');
        showTranscriptionStatus('Upload failed. Please try again.');
    }
}

/**
 * Handle file upload from input
 */
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Validate file type
    const validTypes = ['audio/webm', 'audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/ogg'];
    if (!validTypes.includes(file.type) && !file.name.match(/\.(webm|wav|mp3|ogg)$/i)) {
        showAlert('Please upload a valid audio file (WebM, WAV, MP3, or OGG)', 'warning');
        return;
    }
    
    // Validate file size (max 16MB)
    const maxSize = 16 * 1024 * 1024;
    if (file.size > maxSize) {
        showAlert('File is too large. Maximum size is 16MB.', 'warning');
        return;
    }
    
    await uploadAudio(file);
    
    // Clear input
    event.target.value = '';
}

/**
 * Poll transcription status
 */
async function pollTranscriptionStatus(transcriptId) {
    const maxAttempts = 120; // 10 minutes max (5 second intervals)
    let attempts = 0;
    
    const poll = async () => {
        try {
            const response = await fetch(`/transcribe/status/${transcriptId}`);
            
            if (!response.ok) {
                throw new Error(`Status check failed: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.status === 'completed') {
                handleTranscriptionComplete(data);
                return;
            } else if (data.status === 'error') {
                throw new Error(data.error || 'Transcription failed');
            } else if (data.status === 'processing' || data.status === 'queued') {
                attempts++;
                if (attempts < maxAttempts) {
                    showTranscriptionStatus(`Transcribing... (${attempts * 5}s)`);
                    setTimeout(poll, 5000); // Poll every 5 seconds
                } else {
                    throw new Error('Transcription timeout - please try again');
                }
            } else {
                // Unknown status, keep polling
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(poll, 5000);
                } else {
                    throw new Error('Transcription timeout');
                }
            }
            
        } catch (error) {
            console.error('Polling error:', error);
            showAlert('Transcription failed: ' + error.message, 'danger');
            showTranscriptionStatus('Transcription failed. Please try again.');
        }
    };
    
    // Start polling
    poll();
}

/**
 * Handle transcription completion
 */
function handleTranscriptionComplete(data) {
    currentTranscriptText = data.text || '';
    
    // Display transcript
    displayTranscript(data);
    
    // Enable buttons
    if (createCaseBtn) {
        createCaseBtn.classList.remove('disabled');
        createCaseBtn.removeAttribute('disabled');
    }
    
    if (downloadTextBtn) {
        downloadTextBtn.removeAttribute('disabled');
    }
    
    showAlert('Transcription completed successfully!', 'success');
    console.log('Transcription complete');
}

/**
 * Display transcript in UI
 */
function displayTranscript(data) {
    if (!transcriptionOutput) return;
    
    const text = data.text || 'No text transcribed';
    const entities = data.entities || [];
    const sentiment = data.sentiment_analysis || [];
    const highlights = data.auto_highlights || [];
    
    let html = `
        <div class="p-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="mb-0"><i class="bi bi-check-circle-fill text-success me-2"></i>Transcription Complete</h5>
                <span class="badge bg-success">Ready</span>
            </div>
            
            <div class="transcript-text mb-4">
                <div class="card">
                    <div class="card-body">
                        <p class="mb-0" style="white-space: pre-wrap; line-height: 1.8;">${escapeHtml(text)}</p>
                    </div>
                </div>
            </div>
    `;
    
    // Add entities if available
    if (entities && entities.length > 0) {
        html += `
            <div class="mb-3">
                <h6><i class="bi bi-tags me-2"></i>Detected Entities</h6>
                <div class="d-flex flex-wrap gap-2">
        `;
        entities.slice(0, 10).forEach(entity => {
            html += `<span class="badge bg-info">${escapeHtml(entity.text || entity)}</span>`;
        });
        html += `</div></div>`;
    }
    
    // Add highlights if available
    if (highlights && highlights.results && highlights.results.length > 0) {
        html += `
            <div class="mb-3">
                <h6><i class="bi bi-star me-2"></i>Key Highlights</h6>
                <ul class="list-unstyled">
        `;
        highlights.results.slice(0, 5).forEach(highlight => {
            html += `<li class="mb-2"><i class="bi bi-arrow-right-short text-primary"></i> ${escapeHtml(highlight.text)}</li>`;
        });
        html += `</ul></div>`;
    }
    
    html += `</div>`;
    
    transcriptionOutput.innerHTML = html;
}

/**
 * Show transcription status message
 */
function showTranscriptionStatus(message) {
    if (!transcriptionOutput) return;
    
    transcriptionOutput.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="text-muted">${escapeHtml(message)}</p>
        </div>
    `;
}

/**
 * Clear transcription
 */
function clearTranscription() {
    if (confirm('Are you sure you want to clear the transcription?')) {
        currentTranscriptText = '';
        currentTranscriptId = null;
        
        if (transcriptionOutput) {
            transcriptionOutput.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-mic-fill text-muted" style="font-size: 3rem;"></i>
                    <p class="text-muted">Record audio or upload a file to begin transcription</p>
                </div>
            `;
        }
        
        if (createCaseBtn) {
            createCaseBtn.classList.add('disabled');
            createCaseBtn.setAttribute('disabled', 'disabled');
        }
        
        if (downloadTextBtn) {
            downloadTextBtn.setAttribute('disabled', 'disabled');
        }
        
        console.log('Transcription cleared');
    }
}

/**
 * Download transcript as text file
 */
function downloadTranscript() {
    if (!currentTranscriptText) {
        showAlert('No transcript to download', 'warning');
        return;
    }
    
    const blob = new Blob([currentTranscriptText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcript_${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showAlert('Transcript downloaded', 'success');
}

/**
 * Show create case modal
 */
function showCreateCaseModal() {
    if (!currentTranscriptText) {
        showAlert('No transcript available. Please record or upload audio first.', 'warning');
        return;
    }
    
    // Populate modal with transcript text
    const caseDescriptionInput = document.getElementById('caseDescriptionInput');
    if (caseDescriptionInput) {
        caseDescriptionInput.value = currentTranscriptText;
    }
    
    // Show modal
    const modalElement = document.getElementById('createCaseModal');
    if (modalElement) {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    } else {
        console.error('Create case modal not found');
        showAlert('Modal not found. Please refresh the page.', 'danger');
    }
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.style.minWidth = '300px';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export functions for use in other scripts
window.transcribeApp = {
    getCurrentTranscript: () => currentTranscriptText,
    showCreateCaseModal: showCreateCaseModal
};
