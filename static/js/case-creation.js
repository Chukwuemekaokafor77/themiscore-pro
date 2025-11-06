/**
 * Case Creation from Transcript
 * Handles creating a case with AI analysis from transcribed text
 */

document.addEventListener('DOMContentLoaded', function() {
    const createCaseForm = document.getElementById('createCaseForm');
    
    if (createCaseForm) {
        createCaseForm.addEventListener('submit', handleCaseCreation);
    }
    
    console.log('Case creation module initialized');
});

/**
 * Handle case creation form submission
 */
async function handleCaseCreation(event) {
    event.preventDefault();
    
    // Get form data
    const formData = {
        text: document.getElementById('caseDescriptionInput')?.value || '',
        title: document.getElementById('caseTitleInput')?.value || 'Client Intake',
        client: {
            first_name: document.getElementById('clientFirstName')?.value || '',
            last_name: document.getElementById('clientLastName')?.value || '',
            email: document.getElementById('clientEmail')?.value || '',
            phone: document.getElementById('clientPhone')?.value || '',
            address: document.getElementById('clientAddress')?.value || ''
        }
    };
    
    // Validate required fields
    if (!formData.text.trim()) {
        showAlert('Case description is required', 'warning');
        return;
    }
    
    if (!formData.client.first_name || !formData.client.last_name) {
        showAlert('Client first name and last name are required', 'warning');
        return;
    }
    
    // Show loading state
    const submitButton = event.target.querySelector('button[type="submit"]');
    const originalButtonText = submitButton.innerHTML;
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Creating Case...';
    
    try {
        // Make API call
        const response = await fetch('/api/intake/auto', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Server error: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            handleCaseCreationSuccess(data);
        } else {
            throw new Error(data.error || 'Failed to create case');
        }
        
    } catch (error) {
        console.error('Case creation error:', error);
        showAlert('Failed to create case: ' + error.message, 'danger');
        
        // Restore button
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
    }
}

/**
 * Handle successful case creation
 */
function handleCaseCreationSuccess(data) {
    const caseId = data.case_id;
    const analysis = data.analysis || {};
    
    // Show success alert in modal
    const modalBody = document.querySelector('#createCaseModal .modal-body');
    if (modalBody) {
        const successAlert = document.createElement('div');
        successAlert.className = 'alert alert-success';
        successAlert.innerHTML = `
            <h5 class="alert-heading"><i class="bi bi-check-circle-fill me-2"></i>Case Created Successfully!</h5>
            <hr>
            <p class="mb-2"><strong>Case ID:</strong> ${caseId}</p>
            <p class="mb-2"><strong>Category:</strong> ${analysis.category || 'N/A'}</p>
            <p class="mb-2"><strong>Priority:</strong> ${analysis.priority || 'N/A'}</p>
            <p class="mb-2"><strong>Department:</strong> ${analysis.department || 'N/A'}</p>
            <hr>
            <p class="mb-2"><strong>Actions Created:</strong> ${data.actions_created?.length || 0}</p>
            <p class="mb-2"><strong>Documents Generated:</strong> ${data.documents_created?.length || 0}</p>
            <p class="mb-0"><strong>Deadlines Set:</strong> Multiple critical deadlines tracked</p>
            <hr>
            <p class="mb-0">Redirecting to case page in 3 seconds...</p>
        `;
        
        modalBody.innerHTML = '';
        modalBody.appendChild(successAlert);
    }
    
    // Show success message on page
    showAlert('Case created successfully! Redirecting...', 'success');
    
    // Show case created alert if it exists
    const caseCreatedAlert = document.getElementById('caseCreatedAlert');
    if (caseCreatedAlert) {
        caseCreatedAlert.classList.remove('d-none');
        const viewCaseLink = document.getElementById('viewCaseLink');
        if (viewCaseLink) {
            viewCaseLink.href = `/cases/${caseId}`;
        }
    }
    
    // Log details
    console.log('Case created:', {
        caseId,
        category: analysis.category,
        actionsCreated: data.actions_created?.length,
        documentsCreated: data.documents_created?.length
    });
    
    // Redirect after 3 seconds
    setTimeout(() => {
        window.location.href = `/cases/${caseId}`;
    }, 3000);
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
 * Pre-fill form with AI-suggested data (optional enhancement)
 */
function prefillFormWithAI(transcriptText) {
    // This could use the AI analysis to pre-fill client name, etc.
    // For now, just set the description
    const descInput = document.getElementById('caseDescriptionInput');
    if (descInput) {
        descInput.value = transcriptText;
    }
}

// Export for use in other scripts
window.caseCreation = {
    handleCaseCreation: handleCaseCreation,
    prefillFormWithAI: prefillFormWithAI
};
