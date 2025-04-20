document.addEventListener('DOMContentLoaded', function() {
    // Date range picker for report filtering
    const dateRangeSelector = document.getElementById('reportDateRange');
    if (dateRangeSelector) {
        dateRangeSelector.addEventListener('change', function() {
            const formElement = this.closest('form');
            if (formElement) {
                formElement.submit();
            }
        });
    }
    
    // P&L chart initialization
    const plChartCanvas = document.getElementById('plChart');
    if (plChartCanvas) {
        const plData = JSON.parse(plChartCanvas.dataset.report || '{}');
        
        if (plData && plData.revenue && plData.expenses) {
            // Prepare data for chart
            const revenueData = plData.revenue.map(item => ({
                label: item.account_name,
                value: item.balance
            }));
            
            const expenseData = plData.expenses.map(item => ({
                label: item.account_name,
                value: item.balance
            }));
            
            initPLChart(revenueData, expenseData);
        }
    }
    
    // Function to initialize the P&L chart
    function initPLChart(revenueData, expenseData) {
        // Sort data by value (descending)
        revenueData.sort((a, b) => b.value - a.value);
        expenseData.sort((a, b) => b.value - a.value);
        
        // Get top 5 items for each category, combine the rest
        const processDataForChart = function(data, label) {
            if (data.length <= 5) {
                return {
                    labels: data.map(item => item.label),
                    values: data.map(item => item.value)
                };
            }
            
            // Get top 5
            const top5 = data.slice(0, 5);
            
            // Sum the rest
            const otherSum = data.slice(5).reduce((sum, item) => sum + item.value, 0);
            
            return {
                labels: [...top5.map(item => item.label), `Other ${label}`],
                values: [...top5.map(item => item.value), otherSum]
            };
        };
        
        const revenueChartData = processDataForChart(revenueData, 'Revenue');
        const expenseChartData = processDataForChart(expenseData, 'Expenses');
        
        // Revenue chart
        new Chart(document.getElementById('revenueChart'), {
            type: 'doughnut',
            data: {
                labels: revenueChartData.labels,
                datasets: [{
                    data: revenueChartData.values,
                    backgroundColor: [
                        'rgba(40, 167, 69, 0.8)',  // green
                        'rgba(23, 162, 184, 0.8)', // cyan
                        'rgba(0, 123, 255, 0.8)',  // blue
                        'rgba(255, 193, 7, 0.8)',  // yellow
                        'rgba(111, 66, 193, 0.8)', // purple
                        'rgba(108, 117, 125, 0.8)' // gray for "Other"
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#f8f9fa'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += '$' + context.parsed.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                                return label;
                            }
                        }
                    }
                }
            }
        });
        
        // Expense chart
        new Chart(document.getElementById('expenseChart'), {
            type: 'doughnut',
            data: {
                labels: expenseChartData.labels,
                datasets: [{
                    data: expenseChartData.values,
                    backgroundColor: [
                        'rgba(220, 53, 69, 0.8)',  // red
                        'rgba(253, 126, 20, 0.8)', // orange
                        'rgba(255, 193, 7, 0.8)',  // yellow
                        'rgba(32, 201, 151, 0.8)', // teal
                        'rgba(13, 202, 240, 0.8)', // info
                        'rgba(108, 117, 125, 0.8)' // gray for "Other"
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#f8f9fa'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += '$' + context.parsed.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                                return label;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Export button functionality
    const exportButtons = document.querySelectorAll('.export-report');
    if (exportButtons.length > 0) {
        exportButtons.forEach(button => {
            button.addEventListener('click', function() {
                const reportType = this.getAttribute('data-report-type');
                const exportFormat = this.getAttribute('data-format');
                
                exportReport(reportType, exportFormat);
            });
        });
    }
    
    // Function to handle report exports
    function exportReport(reportType, format) {
        // Get date range
        const startDate = document.getElementById('startDate')?.value || '';
        const endDate = document.getElementById('endDate')?.value || '';
        
        // Build URL with parameters
        let url = `/reports/export?type=${reportType}&format=${format}`;
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate) url += `&end_date=${endDate}`;
        
        // Navigate to export URL
        window.location.href = url;
    }
});
