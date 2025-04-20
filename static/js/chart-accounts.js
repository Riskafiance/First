document.addEventListener('DOMContentLoaded', function() {
    // Account selection modal handling
    const accountSearchInput = document.getElementById('accountSearchInput');
    if (accountSearchInput) {
        accountSearchInput.addEventListener('keyup', function() {
            const searchValue = this.value.toLowerCase();
            const accounts = document.querySelectorAll('.account-item');
            
            accounts.forEach(function(account) {
                const accountText = account.textContent.toLowerCase();
                if (accountText.includes(searchValue)) {
                    account.style.display = '';
                } else {
                    account.style.display = 'none';
                }
            });
        });
    }
    
    // Account form validation
    const accountForm = document.getElementById('accountForm');
    if (accountForm) {
        accountForm.addEventListener('submit', function(event) {
            if (!validateAccountForm()) {
                event.preventDefault();
            }
        });
    }
    
    // Add account type filter
    const accountTypeFilter = document.getElementById('accountTypeFilter');
    if (accountTypeFilter) {
        accountTypeFilter.addEventListener('change', function() {
            filterAccountsByType(this.value);
        });
    }
    
    // Add parent account field handling
    const hasParentCheckbox = document.getElementById('hasParentAccount');
    const parentAccountField = document.getElementById('parentAccountField');
    
    if (hasParentCheckbox && parentAccountField) {
        hasParentCheckbox.addEventListener('change', function() {
            parentAccountField.style.display = this.checked ? 'block' : 'none';
            if (!this.checked) {
                document.getElementById('parentAccountId').value = '';
            }
        });
    }
    
    // Initialize form validation
    function validateAccountForm() {
        let isValid = true;
        
        // Validate account code
        const accountCode = document.getElementById('accountCode');
        if (!accountCode.value.trim()) {
            markInvalid(accountCode, 'Account code is required');
            isValid = false;
        } else if (!/^[0-9]{3,6}$/.test(accountCode.value)) {
            markInvalid(accountCode, 'Account code must be 3-6 digits');
            isValid = false;
        } else {
            markValid(accountCode);
        }
        
        // Validate account name
        const accountName = document.getElementById('accountName');
        if (!accountName.value.trim()) {
            markInvalid(accountName, 'Account name is required');
            isValid = false;
        } else {
            markValid(accountName);
        }
        
        // Validate account type
        const accountType = document.getElementById('accountType');
        if (!accountType.value) {
            markInvalid(accountType, 'Please select an account type');
            isValid = false;
        } else {
            markValid(accountType);
        }
        
        return isValid;
    }
    
    // Helper functions for validation
    function markInvalid(element, message) {
        element.classList.add('is-invalid-custom');
        
        // Create or update feedback message
        let feedback = element.nextElementSibling;
        if (!feedback || !feedback.classList.contains('invalid-feedback-custom')) {
            feedback = document.createElement('div');
            feedback.className = 'invalid-feedback-custom';
            element.parentNode.insertBefore(feedback, element.nextSibling);
        }
        feedback.textContent = message;
    }
    
    function markValid(element) {
        element.classList.remove('is-invalid-custom');
        
        // Remove feedback message if exists
        const feedback = element.nextElementSibling;
        if (feedback && feedback.classList.contains('invalid-feedback-custom')) {
            feedback.remove();
        }
    }
    
    // Filter accounts by type
    function filterAccountsByType(accountType) {
        const accountRows = document.querySelectorAll('.account-row');
        
        if (accountType === 'all') {
            accountRows.forEach(row => {
                row.style.display = '';
            });
        } else {
            accountRows.forEach(row => {
                const rowType = row.getAttribute('data-account-type');
                row.style.display = (rowType === accountType) ? '' : 'none';
            });
        }
    }
    
    // Parent account selection handler
    const selectParentButtons = document.querySelectorAll('.select-parent-account');
    if (selectParentButtons.length > 0) {
        selectParentButtons.forEach(button => {
            button.addEventListener('click', function() {
                const accountId = this.getAttribute('data-account-id');
                const accountName = this.getAttribute('data-account-name');
                
                document.getElementById('parentAccountId').value = accountId;
                document.getElementById('parentAccountName').value = accountName;
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('parentAccountModal'));
                if (modal) {
                    modal.hide();
                }
            });
        });
    }
});
