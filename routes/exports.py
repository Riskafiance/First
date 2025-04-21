from flask import Response, send_file
import pandas as pd
import io
import csv

def export_general_ledger_report(report_data, format='csv'):
    """Helper to export General Ledger report in various formats"""
    if format == 'csv':
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['General Ledger Report'])
        writer.writerow([f"Period: {report_data['start_date']} to {report_data['end_date']}"])
        writer.writerow([])
        
        # For each account, write its transactions
        for account in report_data['accounts']:
            writer.writerow([f"Account: {account['code']} - {account['name']}"])
            writer.writerow(['Starting Balance', '', '', '', '', '', f"${account['starting_balance']:.2f}"])
            writer.writerow(['Date', 'Reference', 'Account', 'Description', 'Debit', 'Credit', 'Balance'])
            
            for entry in account['entries']:
                debit_str = f"${entry['debit_amount']:.2f}" if entry['debit_amount'] > 0 else ""
                credit_str = f"${entry['credit_amount']:.2f}" if entry['credit_amount'] > 0 else ""
                
                writer.writerow([
                    entry['entry_date'].strftime('%Y-%m-%d'),
                    entry['reference'],
                    entry['account_code'],
                    entry['item_description'] or entry['entry_description'],
                    debit_str,
                    credit_str,
                    f"${entry['running_balance']:.2f}"
                ])
            
            writer.writerow(['Ending Balance', '', '', '', '', '', f"${account['ending_balance']:.2f}"])
            writer.writerow([])  # Empty row between accounts
        
        # Totals
        writer.writerow(['Grand Total', '', '', '', f"${report_data['totals']['debit_total']:.2f}", f"${report_data['totals']['credit_total']:.2f}", ''])
        
        # Create response
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment;filename=general_ledger_report.csv'
            }
        )
        
        return response
    
    elif format == 'excel':
        # Create Excel file using pandas
        output = io.BytesIO()
        
        # Create Excel writer
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            header_format = workbook.add_format({
                'bold': True,
                'font_size': 14,
                'align': 'center'
            })
            
            bold_format = workbook.add_format({'bold': True})
            money_format = workbook.add_format({'num_format': '$#,##0.00'})
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            
            # Create worksheet
            worksheet = workbook.add_worksheet('General Ledger')
            
            # Write headers
            worksheet.write(0, 0, 'General Ledger Report', header_format)
            worksheet.write(1, 0, f"Period: {report_data['start_date']} to {report_data['end_date']}")
            
            row = 3
            
            # For each account, write its transactions
            for account in report_data['accounts']:
                worksheet.write(row, 0, f"Account: {account['code']} - {account['name']}", bold_format)
                row += 1
                
                worksheet.write(row, 0, 'Starting Balance', bold_format)
                worksheet.write(row, 6, account['starting_balance'], money_format)
                row += 1
                
                # Column headers
                worksheet.write(row, 0, 'Date', bold_format)
                worksheet.write(row, 1, 'Reference', bold_format)
                worksheet.write(row, 2, 'Account', bold_format)
                worksheet.write(row, 3, 'Description', bold_format)
                worksheet.write(row, 4, 'Debit', bold_format)
                worksheet.write(row, 5, 'Credit', bold_format)
                worksheet.write(row, 6, 'Balance', bold_format)
                row += 1
                
                # Entries
                for entry in account['entries']:
                    worksheet.write(row, 0, entry['entry_date'], date_format)
                    worksheet.write(row, 1, entry['reference'])
                    worksheet.write(row, 2, entry['account_code'])
                    worksheet.write(row, 3, entry['item_description'] or entry['entry_description'])
                    
                    if entry['debit_amount'] > 0:
                        worksheet.write(row, 4, entry['debit_amount'], money_format)
                    
                    if entry['credit_amount'] > 0:
                        worksheet.write(row, 5, entry['credit_amount'], money_format)
                    
                    worksheet.write(row, 6, entry['running_balance'], money_format)
                    row += 1
                
                worksheet.write(row, 0, 'Ending Balance', bold_format)
                worksheet.write(row, 6, account['ending_balance'], money_format)
                row += 2  # Empty row between accounts
            
            # Totals
            worksheet.write(row, 0, 'Grand Total', bold_format)
            worksheet.write(row, 4, report_data['totals']['debit_total'], money_format)
            worksheet.write(row, 5, report_data['totals']['credit_total'], money_format)
            
            # Format column widths
            worksheet.set_column(0, 0, 12)  # Date
            worksheet.set_column(1, 1, 15)  # Reference
            worksheet.set_column(2, 2, 15)  # Account
            worksheet.set_column(3, 3, 40)  # Description
            worksheet.set_column(4, 6, 15)  # Amounts
        
        # Reset pointer
        output.seek(0)
        
        # Create response
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='general_ledger_report.xlsx'
        )
    
    # Default to PDF (requires additional packages like weasyprint)
    else:
        return "Export format not supported", 400