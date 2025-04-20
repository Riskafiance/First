document.addEventListener('DOMContentLoaded', function() {
    // Invoice line items handling
    const addLineItemBtn = document.getElementById('addLineItemBtn');
    const lineItemsContainer = document.getElementById('lineItemsContainer');
    const invoiceForm = document.getElementById('invoiceForm');
    let lineItemCount = document.querySelectorAll('.invoice-line-item').length || 0;
    
    // Add line item to invoice
    if (addLineItemBtn && lineItemsContainer) {
        addLineItemBtn.addEventListener('click', function() {
            addNewLineItem();
        });
    }
    
    // Initialize with at least one line item
    if (lineItemsContainer && lineItemCount === 0) {
        addNewLineItem();
    }
    
    // Form validation before submission
    if (invoiceForm) {
        invoiceForm.addEventListener('submit', function(event) {
            if (!validateInvoiceForm()) {
                event.preventDefault();
            } else {
                calculateInvoiceTotal(); // Ensure total is updated before submit
            }
        });
    }
    
    // Customer selection handler
    const selectCustomerButtons = document.querySelectorAll('.select-customer');
    if (selectCustomerButtons.length > 0) {
        selectCustomerButtons.forEach(button => {
            button.addEventListener('click', function() {
                const customerId = this.getAttribute('data-customer-id');
                const customerName = this.getAttribute('data-customer-name');
                
                document.getElementById('entityId').value = customerId;
                document.getElementById('entityName').value = customerName;
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('customerModal'));
                if (modal) {
                    modal.hide();
                }
            });
        });
    }
    
    // Customer search functionality
    const customerSearchInput = document.getElementById('customerSearchInput');
    if (customerSearchInput) {
        customerSearchInput.addEventListener('keyup', function() {
            const searchValue = this.value.toLowerCase();
            const customers = document.querySelectorAll('.customer-item');
            
            customers.forEach(function(customer) {
                const customerText = customer.textContent.toLowerCase();
                if (customerText.includes(searchValue)) {
                    customer.style.display = '';
                } else {
                    customer.style.display = 'none';
                }
            });
        });
    }
    
    // Account selection for line items
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('select-account')) {
            const button = event.target;
            const accountId = button.getAttribute('data-account-id');
            const accountName = button.getAttribute('data-account-name');
            const lineItemId = button.closest('.modal').getAttribute('data-target-line');
            
            document.getElementById(`account_id_${lineItemId}`).value = accountId;
            document.getElementById(`account_name_${lineItemId}`).value = accountName;
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(button.closest('.modal'));
            if (modal) {
                modal.hide();
            }
        }
    });
    
    // Function to add a new line item to invoice
    function addNewLineItem() {
        lineItemCount++;
        
        const newLineItem = document.createElement('div');
        newLineItem.className = 'invoice-line-item card bg-dark mb-3';
        newLineItem.setAttribute('data-line-number', lineItemCount);
        
        newLineItem.innerHTML = `
            <div class="card-body">
                <div class="row">
                    <div class="col-md-5 mb-2">
                        <label for="description_${lineItemCount}" class="form-label">Description</label>
                        <input type="text" class="form-control" id="description_${lineItemCount}" name="items[${lineItemCount}][description]" required>
                    </div>
                    <div class="col-md-2 mb-2">
                        <label for="quantity_${lineItemCount}" class="form-label">Quantity</label>
                        <input type="number" class="form-control line-quantity" id="quantity_${lineItemCount}" name="items[${lineItemCount}][quantity]" min="0.01" step="0.01" value="1" required>
                    </div>
                    <div class="col-md-2 mb-2">
                        <label for="unit_price_${lineItemCount}" class="form-label">Unit Price</label>
                        <input type="number" class="form-control line-price" id="unit_price_${lineItemCount}" name="items[${lineItemCount}][unit_price]" min="0.01" step="0.01" required>
                    </div>
                    <div class="col-md-2 mb-2">
                        <label for="line_total_${lineItemCount}" class="form-label">Line Total</label>
                        <input type="text" class="form-control line-total" id="line_total_${lineItemCount}" readonly>
                    </div>
                    <div class="col-md-1 mb-2 d-flex align-items-end">
                        <button type="button" class="btn btn-danger remove-line-item" title="Remove Line">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="row mt-2">
                    <div class="col-md-6">
                        <label for="account_name_${lineItemCount}" class="form-label">Revenue Account</label>
                        <div class="input-group">
                            <input type="hidden" id="account_id_${lineItemCount}" name="items[${lineItemCount}][account_id]" required>
                            <input type="text" class="form-control" id="account_name_${lineItemCount}" placeholder="Select an account" readonly required>
                            <button class="btn btn-outline-secondary" type="button" data-bs-toggle="modal" data-bs-target="#accountModal_${lineItemCount}">
                                <i class="fas fa-search"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        lineItemsContainer.appendChild(newLineItem);
        
        // Add account selection modal for this line
        createAccountModal(lineItemCount);
        
        // Add event listeners for calculations
        addLineItemEventListeners(lineItemCount);
    }
    
    // Function to create account selection modal for a line item
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
            title.textContent = 'Select Revenue Account';
            title.id = `accountModalLabel_${lineNumber}`;
        }
        
        document.body.appendChild(newModal);
    }
    
    // Add event listeners to line item inputs for calculations
    function addLineItemEventListeners(lineNumber) {
        const quantityInput = document.getElementById(`quantity_${lineNumber}`);
        const priceInput = document.getElementById(`unit_price_${lineNumber}`);
        const lineTotalInput = document.getElementById(`line_total_${lineNumber}`);
        
        if (quantityInput && priceInput) {
            const updateLineTotal = function() {
                const quantity = parseFloat(quantityInput.value) || 0;
                const price = parseFloat(priceInput.value) || 0;
                const total = quantity * price;
                
                if (lineTotalInput) {
                    lineTotalInput.value = '$' + total.toFixed(2);
                }
                
                // Update invoice total
                calculateInvoiceTotal();
            };
            
            quantityInput.addEventListener('input', updateLineTotal);
            priceInput.addEventListener('input', updateLineTotal);
        }
        
        // Add remove button handler
        const removeButton = document.querySelector(`.invoice-line-item[data-line-number="${lineNumber}"] .remove-line-item`);
        if (removeButton) {
            removeButton.addEventListener('click', function() {
                const lineItem = this.closest('.invoice-line-item');
                lineItem.remove();
                calculateInvoiceTotal();
                
                // Make sure there's at least one line item
                if (document.querySelectorAll('.invoice-line-item').length === 0) {
                    addNewLineItem();
                }
            });
        }
    }
    
    // Calculate and update invoice total
    function calculateInvoiceTotal() {
        const lineItems = document.querySelectorAll('.invoice-line-item');
        let total = 0;
        
        lineItems.forEach(item => {
            const lineNumber = item.getAttribute('data-line-number');
            const quantity = parseFloat(document.getElementById(`quantity_${lineNumber}`).value) || 0;
            const price = parseFloat(document.getElementById(`unit_price_${lineNumber}`).value) || 0;
            
            total += quantity * price;
        });
        
        const totalElement = document.getElementById('invoiceTotal');
        if (totalElement) {
            totalElement.value = total.toFixed(2);
            
            // Update display total
            const displayTotal = document.getElementById('displayInvoiceTotal');
            if (displayTotal) {
                displayTotal.textContent = '$' + total.toFixed(2);
            }
        }
    }
    
    // Validate invoice form before submission
    function validateInvoiceForm() {
        let isValid = true;
        
        // Validate customer
        const entityId = document.getElementById('entityId');
        if (!entityId.value) {
            alert('Please select a customer for this invoice');
            isValid = false;
        }
        
        // Validate issue date
        const issueDate = document.getElementById('issueDate');
        if (!issueDate.value) {
            alert('Please enter an issue date');
            isValid = false;
        }
        
        // Validate due date
        const dueDate = document.getElementById('dueDate');
        if (!dueDate.value) {
            alert('Please enter a due date');
            isValid = false;
        }
        
        // Validate line items
        const lineItems = document.querySelectorAll('.invoice-line-item');
        lineItems.forEach(item => {
            const lineNumber = item.getAttribute('data-line-number');
            
            const description = document.getElementById(`description_${lineNumber}`);
            if (!description.value.trim()) {
                alert('Please enter a description for all line items');
                isValid = false;
            }
            
            const accountId = document.getElementById(`account_id_${lineNumber}`);
            if (!accountId.value) {
                alert('Please select a revenue account for all line items');
                isValid = false;
            }
            
            const quantity = document.getElementById(`quantity_${lineNumber}`);
            if (!quantity.value || parseFloat(quantity.value) <= 0) {
                alert('Quantity must be greater than zero for all line items');
                isValid = false;
            }
            
            const unitPrice = document.getElementById(`unit_price_${lineNumber}`);
            if (!unitPrice.value || parseFloat(unitPrice.value) <= 0) {
                alert('Unit price must be greater than zero for all line items');
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    // Initialize any existing line items when page loads
    document.querySelectorAll('.invoice-line-item').forEach(item => {
        const lineNumber = item.getAttribute('data-line-number');
        addLineItemEventListeners(lineNumber);
    });
    
    // Calculate invoice total on page load
    calculateInvoiceTotal();
});
