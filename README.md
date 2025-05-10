# TE Internet Monitor

A professional monitoring tool for TE Internet usage with advanced features and metrics collection.

## Features

- 🔄 Asynchronous operation for better performance
- 📊 Prometheus metrics integration
- 🔒 Secure credential management using environment variables or command-line options
- ⚡ Rate limiting to prevent API overload
- 🏥 Health checks and automatic recovery
- 📝 Comprehensive logging
- 🔧 YAML-based configuration
- 🔔 Desktop notifications support

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure credentials (choose one method):

   a. Using environment variables (recommended for security):
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env with your credentials
   nano .env
   ```

   b. Using command-line arguments:
   ```bash
   python zwe.py --acctId your_account_id --password your_password
   ```

3. Configure the application in `config.yaml` (already set up with defaults)

## Usage

Run the monitor with your preferred method:

1. Using environment variables:
   ```bash
   python zwe.py
   ```

2. Using command-line arguments:
   ```bash
   python zwe.py --acctId your_account_id --password your_password
   ```

### Command Line Options

- `--config`: Path to configuration file (default: config.yaml)
- `--interval`: Interval between queries in seconds (default: 4000)
- `--acctId`: TE account ID (can also be set via TE_ACCOUNT_ID environment variable)
- `--password`: TE password (can also be set via TE_PASSWORD environment variable)

## Environment Variables

Create a `.env` file with the following variables:

```
# Required: Your TE account credentials
TE_ACCOUNT_ID=your_account_id_here
TE_PASSWORD=your_password_here

# Optional: Notification settings
TE_NOTIFY_ID=your_notify_id_here  # Leave empty if not using notifications
```

## Metrics

The monitor exposes Prometheus metrics on port 8000 (configurable):

- `te_queries_total`: Total number of queries made
- `te_errors_total`: Total number of errors
- `te_data_usage_percent`: Current data usage percentage
- `te_data_remaining_gb`: Remaining data in GB

## Logging

Logs are written to both:
- Console output
- `te_monitor.log` file

## Health Checks

The monitor performs health checks every 5 minutes (configurable) to ensure the service is running properly. If a health check fails, the monitor will attempt to re-authenticate.

## Error Handling

- Automatic retry on failures
- Rate limiting to prevent API overload
- Graceful shutdown on interrupt
- Comprehensive error logging

## Security Notes

- It's recommended to use environment variables for credentials instead of command-line arguments
- The `.env` file should never be committed to version control
- Make sure to set appropriate file permissions on your `.env` file

## Contributing

Feel free to submit issues and enhancement requests!