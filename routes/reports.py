from flask import Blueprint, render_template, request, Response, send_file
from flask_login import login_required
from app import db
from models import AccountType, Account, JournalEntry, JournalItem
from utils import generate_pl_report, generate_balance_sheet
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

@reports_bp.route('/reports/balance-sheet')
@login_required
def balance_sheet():
    """Balance Sheet report"""
    # Get as_of_date
    as_of_date = request.args.get('as_of_date')
    
    # Default to current date if not specified
    if not as_of_date:
        as_of_date = datetime.now().date()
    else:
        as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
    
    # Generate report
    report_data = generate_balance_sheet(as_of_date)
    
    return render_template(
        'report_balance_sheet.html',
        report_data=report_data,
        as_of_date=as_of_date.strftime('%Y-%m-%d')
    )
    
@reports_bp.route('/reports/custom')
@login_required
def custom_report():
    """Custom report with advanced filters"""
    # Get filter parameters
    report_type = request.args.get('report_type', 'general_ledger')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    account_ids = request.args.getlist('account_ids')
    account_type_ids = request.args.getlist('account_type_ids')
    include_unposted = request.args.get('include_unposted', 'false') == 'true'
    group_by = request.args.get('group_by', 'none')
    
    # Default to current month if dates not specified
    if not start_date:
        start_date = datetime.now().date().replace(day=1)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = datetime.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get filter options for the form
    account_types = AccountType.query.all()
    accounts = Account.query.order_by(Account.code).all()
    
    # Process the report based on type and filters
    report_data = None
    if request.args:  # Only generate report if filters are submitted
        if report_type == 'general_ledger':
            report_data = generate_general_ledger(
                start_date, 
                end_date, 
                account_ids, 
                account_type_ids,
                include_unposted
            )
    
    return render_template(
        'report_custom.html',
        report_type=report_type,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        account_ids=account_ids,
        account_type_ids=account_type_ids,
        include_unposted=include_unposted,
        group_by=group_by,
        account_types=account_types,
        accounts=accounts,
        report_data=report_data
    )

@reports_bp.route('/reports/export')
@login_required
def export_report():
    """Export reports in various formats"""
    report_type = request.args.get('type', 'pl')
    export_format = request.args.get('format', 'csv')
    
    # Different parameters based on report type
    if report_type == 'pl':
        # Get date range for P&L report
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
        
        # Generate P&L report
        report_data = generate_pl_report(start_date, end_date)
        return export_pl_report(report_data, export_format)
    
    elif report_type == 'bs':
        # Get as_of_date for Balance Sheet
        as_of_date = request.args.get('as_of_date')
        
        # Default to current date if not specified
        if not as_of_date:
            as_of_date = datetime.now().date()
        else:
            as_of_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
        
        # Generate Balance Sheet report
        report_data = generate_balance_sheet(as_of_date)
        return export_balance_sheet_report(report_data, export_format)
    
    elif report_type == 'custom':
        # Get custom report parameters
        custom_report_type = request.args.get('report_type', 'general_ledger')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        account_ids = request.args.getlist('account_ids')
        account_type_ids = request.args.getlist('account_type_ids')
        include_unposted = request.args.get('include_unposted', 'false') == 'true'
        
        # Default to current month if dates not specified
        if not start_date:
            start_date = datetime.now().date().replace(day=1)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        if not end_date:
            end_date = datetime.now().date()
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Generate report based on type
        if custom_report_type == 'general_ledger':
            report_data = generate_general_ledger(
                start_date, 
                end_date, 
                account_ids, 
                account_type_ids,
                include_unposted
            )
            return export_general_ledger_report(report_data, export_format)
        
        # Add more custom report types here as needed
        
        return "Custom report type not supported", 400
    
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
        
def export_balance_sheet_report(report_data, format='csv'):
    """Helper to export Balance Sheet report in various formats"""
    if format == 'csv':
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Balance Sheet'])
        writer.writerow([f"As of: {report_data['as_of_date']}"])
        writer.writerow([])
        
        # Assets section
        writer.writerow(['Assets'])
        writer.writerow(['Account Code', 'Account Name', 'Amount'])
        for item in report_data['assets']:
            writer.writerow([
                item['account_code'],
                item['account_name'],
                f"${item['balance']:.2f}"
            ])
        
        writer.writerow(['', 'Total Assets', f"${report_data['totals']['assets']:.2f}"])
        writer.writerow([])
        
        # Liabilities section
        writer.writerow(['Liabilities'])
        writer.writerow(['Account Code', 'Account Name', 'Amount'])
        for item in report_data['liabilities']:
            writer.writerow([
                item['account_code'],
                item['account_name'],
                f"${item['balance']:.2f}"
            ])
        
        writer.writerow(['', 'Total Liabilities', f"${report_data['totals']['liabilities']:.2f}"])
        writer.writerow([])
        
        # Equity section
        writer.writerow(['Equity'])
        writer.writerow(['Account Code', 'Account Name', 'Amount'])
        for item in report_data['equity']:
            writer.writerow([
                item['account_code'],
                item['account_name'],
                f"${item['balance']:.2f}"
            ])
        
        writer.writerow(['', 'Total Equity', f"${report_data['totals']['equity']:.2f}"])
        writer.writerow([])
        
        # Summary
        writer.writerow(['Total Liabilities and Equity', '', f"${report_data['totals']['liabilities_and_equity']:.2f}"])
        
        # Create response
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment;filename=balance_sheet_report.csv'
            }
        )
        
        return response
    
    elif format == 'excel':
        # Create Excel file using pandas
        output = io.BytesIO()
        
        # Create dataframes for each section
        assets_df = pd.DataFrame(report_data['assets'])
        liabilities_df = pd.DataFrame(report_data['liabilities'])
        equity_df = pd.DataFrame(report_data['equity'])
        
        # Create Excel writer
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Write header
            workbook = writer.book
            header_format = workbook.add_format({
                'bold': True,
                'font_size': 14,
                'align': 'center'
            })
            
            # Get the worksheet
            worksheet = writer.sheets.get('Sheet1') or workbook.add_worksheet('Balance Sheet')
            
            # Write headers
            worksheet.write(0, 0, 'Balance Sheet', header_format)
            worksheet.write(1, 0, f"As of: {report_data['as_of_date']}")
            
            # Write assets section
            row = 3
            worksheet.write(row, 0, 'Assets', workbook.add_format({'bold': True}))
            row += 1
            worksheet.write(row, 0, 'Account Code')
            worksheet.write(row, 1, 'Account Name')
            worksheet.write(row, 2, 'Amount')
            row += 1
            
            # Write asset rows
            for asset in report_data['assets']:
                worksheet.write(row, 0, asset['account_code'])
                worksheet.write(row, 1, asset['account_name'])
                worksheet.write(row, 2, float(asset['balance']))
                row += 1
            
            # Write asset total
            worksheet.write(row, 1, 'Total Assets', workbook.add_format({'bold': True}))
            worksheet.write(row, 2, float(report_data['totals']['assets']))
            row += 2
            
            # Write liabilities section
            worksheet.write(row, 0, 'Liabilities', workbook.add_format({'bold': True}))
            row += 1
            worksheet.write(row, 0, 'Account Code')
            worksheet.write(row, 1, 'Account Name')
            worksheet.write(row, 2, 'Amount')
            row += 1
            
            # Write liability rows
            for liability in report_data['liabilities']:
                worksheet.write(row, 0, liability['account_code'])
                worksheet.write(row, 1, liability['account_name'])
                worksheet.write(row, 2, float(liability['balance']))
                row += 1
            
            # Write liability total
            worksheet.write(row, 1, 'Total Liabilities', workbook.add_format({'bold': True}))
            worksheet.write(row, 2, float(report_data['totals']['liabilities']))
            row += 2
            
            # Write equity section
            worksheet.write(row, 0, 'Equity', workbook.add_format({'bold': True}))
            row += 1
            worksheet.write(row, 0, 'Account Code')
            worksheet.write(row, 1, 'Account Name')
            worksheet.write(row, 2, 'Amount')
            row += 1
            
            # Write equity rows
            for equity_item in report_data['equity']:
                worksheet.write(row, 0, equity_item['account_code'])
                worksheet.write(row, 1, equity_item['account_name'])
                worksheet.write(row, 2, float(equity_item['balance']))
                row += 1
            
            # Write equity total
            worksheet.write(row, 1, 'Total Equity', workbook.add_format({'bold': True}))
            worksheet.write(row, 2, float(report_data['totals']['equity']))
            row += 2
            
            # Write total liabilities and equity
            worksheet.write(row, 1, 'Total Liabilities and Equity', workbook.add_format({'bold': True}))
            worksheet.write(row, 2, float(report_data['totals']['liabilities_and_equity']))
            
            # Format column widths
            worksheet.set_column(0, 0, 15)  # Account code column
            worksheet.set_column(1, 1, 30)  # Account name column
            worksheet.set_column(2, 2, 15)  # Amount column
        
        # Reset pointer
        output.seek(0)
        
        # Create response
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='balance_sheet_report.xlsx'
        )
    
    # Default to PDF (requires additional packages like weasyprint)
    else:
        return "Export format not supported", 400
