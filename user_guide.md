# Tenant Dashboard User Guide

## Introduction

The Tenant Dashboard is a comprehensive web application designed to manage rental agreements and track critical dates for property management. This system automatically extracts information from uploaded PDF rental agreements using advanced OCR technology and AI analysis, providing you with a centralized view of all tenant information and important deadlines.

## Getting Started

### System Requirements

Before using the Tenant Dashboard, ensure your system meets these requirements:
- A modern web browser (Chrome, Firefox, Safari, or Edge)
- Internet connection for AI-powered text extraction
- PDF files with readable text content

### Accessing the Application

Launch the Tenant Dashboard by opening your web browser and navigating to the application URL. The main dashboard will display all active rental agreements in a comprehensive table format.

## Core Features

### Dashboard Overview

The main dashboard presents all your rental agreements in an organized table format. Each row represents a single rental agreement with detailed information extracted automatically from the uploaded documents.

The dashboard displays the following key information for each agreement:
- Tenant name and company details
- Physical location and space occupied
- Rental period and financial terms
- Agreement dates and lock-in periods
- Maintenance and escalation details
- Alert status indicators

### Uploading New Agreements

Adding new rental agreements to the system is straightforward and automated:

1. Locate the file upload section at the top of the dashboard
2. Click the "Choose File" button to select a PDF rental agreement
3. Ensure the PDF contains readable text content
4. Click "Upload Agreement" to process the document

The system will automatically:
- Convert the PDF to images for text extraction
- Use OCR technology to read the document content
- Apply AI analysis to extract relevant information
- Populate all data fields automatically
- Add the agreement to your active agreements list

### Understanding Alert Status

The system provides intelligent alerting based on lock-in period deadlines:

**Green Highlight (Approaching)**: Appears when the lock-in period is within one month of expiration. This indicates you should begin preparing for potential tenant decisions regarding lease renewal or termination.

**Gray Highlight (Grace Period)**: Shows when the lock-in period has ended but is within one month of the deadline. This represents a critical window for follow-up actions.

**Red Highlight (Overdue)**: Indicates the lock-in period has been exceeded by more than one month. This requires immediate attention and follow-up with the tenant.

**No Highlight**: Normal status when the lock-in period is more than one month away from expiration.

### Data Fields Explained

**Tenant Information**
- Tenant Name: Company or individual name
- Place Occupied: Physical location and space details
- Period of Rent: Duration of the rental agreement

**Financial Terms**
- Rent Amount: Monthly rental rate per square foot
- Maintenance: Common area maintenance charges
- Rent Escalation: Annual percentage increase in rent
- Next Rent Escalation: Date when the next increase takes effect

**Agreement Timeline**
- Agreement Start Date: When the lease begins
- Agreement Expiry Date: When the lease term ends
- Lock In Period: Minimum commitment period
- Lock In Period End Date: Critical deadline for tenant decisions

**Contract Details**
- Rental Period vs Lock In Period: Whether the total rental period exceeds the lock-in commitment
- Upload Timestamp: When the agreement was added to the system

## Managing Agreements

### Viewing Agreement Details

All agreement information is displayed in a comprehensive table format. The table automatically sorts agreements and provides a complete overview of your rental portfolio. Use the horizontal scroll bar to view all columns on smaller screens.

### Deleting Agreements

When you need to remove an agreement from the active list:

1. Locate the agreement in the dashboard table
2. Click the red "Delete" button in the Actions column
3. Confirm the deletion when prompted

Deleted agreements are automatically moved to the archive system rather than being permanently removed, allowing you to restore them if needed.

### Archive Management

The archive system provides a complete history of all agreements that have been removed from the active dashboard:

**Accessing the Archive**
- Click the "View Archive" button in the top-right corner of the dashboard
- The archive page displays all previously deleted agreements

**Restoring Agreements**
- In the archive view, locate the agreement you want to restore
- Click the green "Restore" button in the Actions column
- Confirm the restoration when prompted
- The agreement will return to your active dashboard

**Archive Information**
- Archived agreements show the date they were removed from the active list
- All original agreement data is preserved in the archive
- You can restore agreements at any time with full data integrity

## Advanced Features

### Automatic Data Extraction

The system uses sophisticated technology to extract information from your rental agreements:

**OCR Processing**: Converts scanned PDF documents into readable text

**AI Analysis**: Uses advanced language models to identify and extract relevant information

**Data Validation**: Ensures extracted data is properly formatted and complete

### Real-time Updates

The dashboard automatically updates alert statuses based on current dates:
- Lock-in period alerts are recalculated daily
- Color coding updates automatically as deadlines approach
- No manual intervention required for status updates

### Data Persistence

All agreement information is securely stored and backed up:
- Data is saved in JSON format for reliability
- Upload timestamps track when agreements were added
- Unique identifiers ensure data integrity across operations

## Troubleshooting

### Common Issues

**PDF Upload Failures**
- Ensure the PDF contains readable text content
- Check that the file size is reasonable
- Verify the PDF is not password-protected

**Incomplete Data Extraction**
- Some agreements may have non-standard formatting
- Review extracted data for accuracy after upload
- Contact support if extraction quality is consistently poor

**Alert Status Issues**
- Alert colors update automatically based on current dates
- Refresh the page if alerts appear incorrect
- Check that agreement dates are in the correct format

### Best Practices

**File Preparation**
- Use high-quality PDF scans for best text extraction
- Ensure all text in the agreement is clearly readable
- Avoid heavily formatted or image-heavy documents

**Data Verification**
- Review extracted information after each upload
- Verify critical dates and financial terms
- Update any incorrect information manually if needed

**Regular Maintenance**
- Check the dashboard regularly for approaching deadlines
- Review archived agreements periodically
- Keep the system updated with new agreements

## Security and Privacy

The Tenant Dashboard prioritizes data security:
- All uploaded files are processed locally
- No sensitive information is transmitted to external servers
- Data is stored securely in your local environment
- Access is restricted to authorized users only

## Support and Maintenance

For technical support or questions about the Tenant Dashboard:
- Review this user guide for common solutions
- Check the application logs for error details
- Ensure all system requirements are met
- Contact your system administrator for additional assistance

The Tenant Dashboard provides a powerful and intuitive solution for managing rental agreements. By following this guide, you'll be able to efficiently upload, monitor, and manage all aspects of your rental portfolio with automated alerts and comprehensive data tracking.