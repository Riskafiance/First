from flask import Blueprint, render_template, request, Response, send_file
from flask_login import login_required
from app import db
from models import AccountType, Account, JournalEntry, JournalItem
from utils import generate_pl_report
from datetime import datetime, timedelta
import pandas as pd
import io
import csv

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
@login_required
def index():
    """Reports dashboard"""
    return render_template('reports.html')

@reports_bp.route('/reports/profit-loss')
@login_required
def pl():
    """Profit and Loss report"""
    # Get date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Default to current month if not specified
    if not start_date:
        start_date = datetime.now().date().replace(day=1)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = datetime.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Generate report
    report_data = generate_pl_report(start_date, end_date)
    
    return render_template(
        'report_pl.html',
        report_data=report_data,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

@reports_bp.route('/reports/export')
@login_required
def export_report():
    """Export reports in various formats"""
    report_type = request.args.get('type', 'pl')
    export_format = request.args.get('format', 'csv')
    
    # Get date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Default to current month if not specified
    if not start_date:
        start_date = datetime.now().date().replace(day=1)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = datetime.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Generate requested report
    if report_type == 'pl':
        report_data = generate_pl_report(start_date, end_date)
        return export_pl_report(report_data, export_format)
    
    # Default response if report type not recognized
    return "Report type not supported", 400

def export_pl_report(report_data, format='csv'):
    """Helper to export P&L report in various formats"""
    if format == 'csv':
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Profit and Loss Report'])
        writer.writerow([f"Period: {report_data['period']}"])
        writer.writerow([])
        
        # Revenue section
        writer.writerow(['Revenue'])
        writer.writerow(['Account Code', 'Account Name', 'Amount'])
        for item in report_data['revenue']:
            writer.writerow([
                item['account_code'],
                item['account_name'],
                f"${item['balance']:.2f}"
            ])
        
        writer.writerow(['', 'Total Revenue', f"${report_data['totals']['revenue']:.2f}"])
        writer.writerow([])
        
        # Expenses section
        writer.writerow(['Expenses'])
        writer.writerow(['Account Code', 'Account Name', 'Amount'])
        for item in report_data['expenses']:
            writer.writerow([
                item['account_code'],
                item['account_name'],
                f"${item['balance']:.2f}"
            ])
        
        writer.writerow(['', 'Total Expenses', f"${report_data['totals']['expenses']:.2f}"])
        writer.writerow([])
        
        # Summary
        writer.writerow(['Net Income', '', f"${report_data['totals']['net_income']:.2f}"])
        
        # Create response
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment;filename=profit_loss_report.csv'
            }
        )
        
        return response
    
    elif format == 'excel':
        # Create Excel file using pandas
        output = io.BytesIO()
        
        # Create dataframes for each section
        revenue_df = pd.DataFrame(report_data['revenue'])
        expenses_df = pd.DataFrame(report_data['expenses'])
        
        # Create Excel writer
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Write header
            workbook = writer.book
            header_format = workbook.add_format({
                'bold': True,
                'font_size': 14,
                'align': 'center'
            })
            
            # Write revenue sheet
            revenue_df.to_excel(writer, sheet_name='P&L Report', startrow=3, startcol=0, index=False)
            
            # Write expenses sheet
            expenses_df.to_excel(writer, sheet_name='P&L Report', startrow=len(revenue_df) + 6, startcol=0, index=False)
            
            # Get the worksheet
            worksheet = writer.sheets['P&L Report']
            
            # Write headers
            worksheet.write(0, 0, 'Profit and Loss Report', header_format)
            worksheet.write(1, 0, f"Period: {report_data['period']}")
            worksheet.write(2, 0, 'Revenue', workbook.add_format({'bold': True}))
            
            # Write revenue total
            revenue_total_row = len(revenue_df) + 3
            worksheet.write(revenue_total_row, 0, 'Total Revenue')
            worksheet.write(revenue_total_row, 2, report_data['totals']['revenue'])
            
            # Write expenses header
            worksheet.write(revenue_total_row + 2, 0, 'Expenses', workbook.add_format({'bold': True}))
            
            # Write expenses total
            expenses_total_row = revenue_total_row + 3 + len(expenses_df)
            worksheet.write(expenses_total_row, 0, 'Total Expenses')
            worksheet.write(expenses_total_row, 2, report_data['totals']['expenses'])
            
            # Write net income
            worksheet.write(expenses_total_row + 2, 0, 'Net Income', workbook.add_format({'bold': True}))
            worksheet.write(expenses_total_row + 2, 2, report_data['totals']['net_income'])
        
        # Reset pointer
        output.seek(0)
        
        # Create response
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='profit_loss_report.xlsx'
        )
    
    # Default to PDF (requires additional packages like weasyprint)
    else:
        return "Export format not supported", 400
