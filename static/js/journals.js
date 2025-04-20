document.addEventListener('DOMContentLoaded', function() {
    // Journal entry line items handling
    const addJournalItemBtn = document.getElementById('addJournalItemBtn');
    const journalItemsContainer = document.getElementById('journalItemsContainer');
    const journalForm = document.getElementById('journalEntryForm');
    let journalItemCount = document.querySelectorAll('.journal-item-row').length || 0;
    
    // Add journal item
    if (addJournalItemBtn && journalItemsContainer) {
        addJournalItemBtn.addEventListener('click', function() {
            addNewJournalItem();
        });
    }
    
    // Initialize with at least one debit and one credit line
    if (journalItemsContainer && journalItemCount === 0) {
        addNewJournalItem('debit');
        addNewJournalItem('credit');
    }
    
    // Form validation before submission
    if (journalForm) {
        journalForm.addEventListener('submit', function(event) {
            if (!validateJournalForm()) {
                event.preventDefault();
            }
        });
    }
    
    // Account search functionality
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
    
    // Account selection for journal items
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('select-account')) {
            const button = event.target;
            const accountId = button.getAttribute('data-account-id');
            const accountName = button.getAttribute('data-account-name');
            const journalItemId = button.closest('.modal').getAttribute('data-target-line');
            
            document.getElementById(`account_id_${journalItemId}`).value = accountId;
            document.getElementById(`account_name_${journalItemId}`).value = accountName;
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(button.closest('.modal'));
            if (modal) {
                modal.hide();
            }
        }
    });
    
    // Function to add a new journal entry line
    function addNewJournalItem(defaultType = null) {
        journalItemCount++;
        
        const newJournalItem = document.createElement('div');
        newJournalItem.className = 'journal-item-row';
        newJournalItem.setAttribute('data-line-number', journalItemCount);
        
        const isDebit = defaultType === 'debit' ? 'checked' : '';
        const isCredit = defaultType === 'credit' ? 'checked' : '';
        
        newJournalItem.innerHTML = `
            <div class="card bg-dark mb-3">
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-5 mb-2">
                            <label for="account_name_${journalItemCount}" class="form-label">Account</label>
                            <div class="input-group">
                                <input type="hidden" id="account_id_${journalItemCount}" name="items[${journalItemCount}][account_id]" required>
                                <input type="text" class="form-control" id="account_name_${journalItemCount}" placeholder="Select an account" readonly required>
                                <button class="btn btn-outline-secondary" type="button" data-bs-toggle="modal" data-bs-target="#accountModal_${journalItemCount}">
                                    <i class="fas fa-search"></i>
                                </button>
                            </div>
                        </div>
                        <div class="col-md-4 mb-2">
                            <label for="description_${journalItemCount}" class="form-label">Description</label>
                            <input type="text" class="form-control" id="description_${journalItemCount}" name="items[${journalItemCount}][description]">
                        </div>
                        <div class="col-md-2 mb-2">
                            <label class="form-label d-block">Type</label>
                            <div class="btn-group" role="group" aria-label="Entry type">
                                <input type="radio" class="btn-check entry-type" name="items[${journalItemCount}][entry_type]" id="debit_${journalItemCount}" value="debit" ${isDebit} required>
                                <label class="btn btn-outline-primary" for="debit_${journalItemCount}">Debit</label>
                                <input type="radio" class="btn-check entry-type" name="items[${journalItemCount}][entry_type]" id="credit_${journalItemCount}" value="credit" ${isCredit}>
                                <label class="btn btn-outline-primary" for="credit_${journalItemCount}">Credit</label>
                            </div>
                        </div>
                        <div class="col-md-1 mb-2 d-flex align-items-end">
                            <button type="button" class="btn btn-danger remove-journal-item" title="Remove Line">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                    <div class="row mt-2">
                        <div class="col-md-5 mb-2">
                            <label for="amount_${journalItemCount}" class="form-label">Amount</label>
                            <div class="input-group">
                                <span class="input-group-text">$</span>
                                <input type="number" class="form-control entry-amount" id="amount_${journalItemCount}" name="items[${journalItemCount}][amount]" min="0.01" step="0.01" required>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        journalItemsContainer.appendChild(newJournalItem);
        
        // Add account selection modal for this line
        createAccountModal(journalItemCount);
        
        // Add event listeners for the new journal item
        addJournalItemEventListeners(journalItemCount);
        
        // Update totals
        updateJournalTotals();
    }
    
    // Function to create account selection modal for a journal item
    function createAccountModal(lineNumber) {
        // Get the accounts data from the existing modal
        const existingModal = document.getElementById('accountModalTemplate');
        if (!existingModal) return;
        
        const modalContent = existingModal.querySelector('.modal-content').cloneNode(true);
        
        // Create new modal
        const newModal = document.createElement('div');
        newModal.className = 'modal fade';
        newModal.id = `accountModal_${lineNumber}`;
        newModal.setAttribute('tabindex', '-1');
        newModal.setAttribute('aria-labelledby', `accountModalLabel_${lineNumber}`);
        newModal.setAttribute('aria-hidden', 'true');
        newModal.setAttribute('data-target-line', lineNumber);
        
        newModal.innerHTML = '<div class="modal-dialog modal-lg"></div>';
        newModal.querySelector('.modal-dialog').appendChild(modalContent);
        
        // Update modal title
        const title = newModal.querySelector('.modal-title');
        if (title) {
            title.textContent = 'Select Account';
            title.id = `accountModalLabel_${lineNumber}`;
        }
        
        document.body.appendChild(newModal);
    }
    
    // Add event listeners to journal item inputs
    function addJournalItemEventListeners(lineNumber) {
        // Add remove button handler
        const removeButton = document.querySelector(`.journal-item-row[data-line-number="${lineNumber}"] .remove-journal-item`);
        if (removeButton) {
            removeButton.addEventListener('click', function() {
                const journalItem = this.closest('.journal-item-row');
                journalItem.remove();
                updateJournalTotals();
                
                // Make sure there's at least one debit and one credit line
                ensureDebitCreditLines();
            });
        }
        
        // Add amount change handler
        const amountInput = document.getElementById(`amount_${lineNumber}`);
        if (amountInput) {
            amountInput.addEventListener('input', updateJournalTotals);
        }
        
        // Add type change handler
        const debitRadio = document.getElementById(`debit_${lineNumber}`);
        const creditRadio = document.getElementById(`credit_${lineNumber}`);
        
        if (debitRadio && creditRadio) {
            debitRadio.addEventListener('change', updateJournalTotals);
            creditRadio.addEventListener('change', updateJournalTotals);
        }
    }
    
    // Ensure there's at least one debit and one credit line
    function ensureDebitCreditLines() {
        const items = document.querySelectorAll('.journal-item-row');
        
        if (items.length === 0) {
            // If no items, add one debit and one credit
            addNewJournalItem('debit');
            addNewJournalItem('credit');
            return;
        }
        
        // Check if we have both debit and credit lines
        let hasDebit = false;
        let hasCredit = false;
        
        items.forEach(item => {
            const lineNumber = item.getAttribute('data-line-number');
            const debitRadio = document.getElementById(`debit_${lineNumber}`);
            const creditRadio = document.getElementById(`credit_${lineNumber}`);
            
            if (debitRadio && debitRadio.checked) {
                hasDebit = true;
            }
            
            if (creditRadio && creditRadio.checked) {
                hasCredit = true;
            }
        });
        
        if (!hasDebit) {
            addNewJournalItem('debit');
        }
        
        if (!hasCredit) {
            addNewJournalItem('credit');
        }
    }
    
    // Update journal entry totals
    function updateJournalTotals() {
        const items = document.querySelectorAll('.journal-item-row');
        let totalDebit = 0;
        let totalCredit = 0;
        
        items.forEach(item => {
            const lineNumber = item.getAttribute('data-line-number');
            const amountInput = document.getElementById(`amount_${lineNumber}`);
            const debitRadio = document.getElementById(`debit_${lineNumber}`);
            
            if (amountInput && debitRadio) {
                const amount = parseFloat(amountInput.value) || 0;
                
                if (debitRadio.checked) {
                    totalDebit += amount;
                } else {
                    totalCredit += amount;
                }
            }
        });
        
        // Update displayed totals
        const debitTotalElement = document.getElementById('totalDebit');
        const creditTotalElement = document.getElementById('totalCredit');
        const differenceElement = document.getElementById('differenceAmount');
        
        if (debitTotalElement) {
            debitTotalElement.textContent = '$' + totalDebit.toFixed(2);
        }
        
        if (creditTotalElement) {
            creditTotalElement.textContent = '$' + totalCredit.toFixed(2);
        }
        
        if (differenceElement) {
            const difference = Math.abs(totalDebit - totalCredit);
            differenceElement.textContent = '$' + difference.toFixed(2);
            
            const balancedMessage = document.getElementById('balancedMessage');
            const unbalancedMessage = document.getElementById('unbalancedMessage');
            
            if (difference < 0.01) {
                // Entries are balanced (allowing for small rounding errors)
                balancedMessage.style.display = 'block';
                unbalancedMessage.style.display = 'none';
            } else {
                balancedMessage.style.display = 'none';
                unbalancedMessage.style.display = 'block';
            }
        }
    }
    
    // Validate journal entry form before submission
    function validateJournalForm() {
        let isValid = true;
        
        // Validate entry date
        const entryDate = document.getElementById('entryDate');
        if (!entryDate.value) {
            alert('Please enter a date for the journal entry');
            isValid = false;
        }
        
        // Make sure entries are balanced
        const items = document.querySelectorAll('.journal-item-row');
        let totalDebit = 0;
        let totalCredit = 0;
        
        items.forEach(item => {
            const lineNumber = item.getAttribute('data-line-number');
            const accountId = document.getElementById(`account_id_${lineNumber}`);
            const amountInput = document.getElementById(`amount_${lineNumber}`);
            const debitRadio = document.getElementById(`debit_${lineNumber}`);
            
            // Check if account is selected
            if (!accountId.value) {
                alert('Please select an account for all journal items');
                isValid = false;
            }
            
            // Check if amount is valid
            if (!amountInput.value || parseFloat(amountInput.value) <= 0) {
                alert('Amount must be greater than zero for all journal items');
                isValid = false;
            }
            
            if (amountInput && debitRadio) {
                const amount = parseFloat(amountInput.value) || 0;
                
                if (debitRadio.checked) {
                    totalDebit += amount;
                } else {
                    totalCredit += amount;
                }
            }
        });
        
        // Check if debits and credits are balanced
        const difference = Math.abs(totalDebit - totalCredit);
        if (difference >= 0.01) {
            alert('Journal entry must be balanced (debits must equal credits)');
            isValid = false;
        }
        
        return isValid;
    }
    
    // Initialize any existing journal items when page loads
    document.querySelectorAll('.journal-item-row').forEach(item => {
        const lineNumber = item.getAttribute('data-line-number');
        addJournalItemEventListeners(lineNumber);
    });
    
    // Update totals on page load
    updateJournalTotals();
});
