document.addEventListener('DOMContentLoaded', function() {
    // Function to initialize charts
    function initCharts() {
        initFinancialSummaryChart();
        initMonthlyTrendsChart();
        initTopCustomersChart();
    }
    
    // Financial summary chart (Income vs Expenses)
    function initFinancialSummaryChart() {
        const ctx = document.getElementById('financialSummaryChart');
        if (!ctx) return;
        
        // Get data from the data attribute
        const summaryData = JSON.parse(ctx.dataset.summary || '{}');
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Income', 'Expenses'],
                datasets: [{
                    data: [summaryData.income || 0, summaryData.expenses || 0],
                    backgroundColor: [
                        'rgba(40, 167, 69, 0.8)',  // Green for income
                        'rgba(220, 53, 69, 0.8)'   // Red for expenses
                    ],
                    borderColor: [
                        'rgba(40, 167, 69, 1)',
                        'rgba(220, 53, 69, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'bottom',
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
    
    // Monthly trends chart
    function initMonthlyTrendsChart() {
        const ctx = document.getElementById('monthlyTrendsChart');
        if (!ctx) return;
        
        // Get data from the data attribute
        const trendsData = JSON.parse(ctx.dataset.trends || '[]');
        
        const months = trendsData.map(item => item.month);
        const incomeData = trendsData.map(item => item.income);
        const expenseData = trendsData.map(item => item.expenses);
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: months,
                datasets: [
                    {
                        label: 'Income',
                        data: incomeData,
                        backgroundColor: 'rgba(40, 167, 69, 0.7)',
                        borderColor: 'rgba(40, 167, 69, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Expenses',
                        data: expenseData,
                        backgroundColor: 'rgba(220, 53, 69, 0.7)',
                        borderColor: 'rgba(220, 53, 69, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#f8f9fa'
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#f8f9fa',
                            callback: function(value) {
                                return '$' + value.toLocaleString('en-US');
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#f8f9fa'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += '$' + context.parsed.y.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                                return label;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Top customers chart
    function initTopCustomersChart() {
        const ctx = document.getElementById('topCustomersChart');
        if (!ctx) return;
        
        // Get data from the data attribute
        const customersData = JSON.parse(ctx.dataset.customers || '[]');
        
        const customerNames = customersData.map(item => item.name);
        const salesData = customersData.map(item => item.sales);
        
        new Chart(ctx, {
            type: 'horizontalBar',
            data: {
                labels: customerNames,
                datasets: [{
                    label: 'Sales Amount',
                    data: salesData,
                    backgroundColor: 'rgba(13, 110, 253, 0.7)',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#f8f9fa',
                            callback: function(value) {
                                return '$' + value.toLocaleString('en-US');
                            }
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#f8f9fa'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = 'Sales: ';
                                label += '$' + context.parsed.x.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                                return label;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Date range picker for filtering dashboard data
    const dateRangePicker = document.getElementById('dashboardDateRange');
    if (dateRangePicker) {
        dateRangePicker.addEventListener('change', function() {
            const formElement = this.closest('form');
            if (formElement) {
                formElement.submit();
            }
        });
    }
    
    // Initialize charts
    initCharts();
});
