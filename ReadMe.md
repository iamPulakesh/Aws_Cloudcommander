# Cloud Commander

Cloud Commander is a powerful, secure and user-friendly Discord bot that lets users manage their AWS resources directly from a designated channel. It is built with Python, Boto3 and Discord.py.

## Features

- Secure IAM Role-based Access via AWS STS
- Region-per-user support (`/set-region`, `/switch-region`)
- EC2 management: list, start, stop, and metrics
- EBS & RDS: volume/status checks, metrics, start/stop RDS
- S3 & Lambda: list buckets/functions, usage stats
- CloudFormation support: list & describe stacks
- Network insights: VPCs, Subnets, NACLs, Route Tables and much more
- CloudWatch metrics

## Project Structure

```
├── bot.py              # Bot logics
├── roles.json          # Stores user-role-region mapping
├── .env               # Contains bot token
└── requirements.txt   # Project dependencies
```

## Setup Instructions

### 1. Create Your IAM Role

- Create an IAM Role with the necessary AWS permissions
- Enable `sts:AssumeRole` and note the Role ARN

### 2. Configure the Bot

Create a `.env` file and add:

```env
BOT_TOKEN=your_discord_bot_token
```

### 3. Install Dependencies

Make sure you have Python 3.10+

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 4. Run the Bot

```bash
python bot.py
```

## Usage Guide

### First-Time Setup

1. Go to the `#cloud-commander` channel
2. Run `/setup-role <your_iam_role_arn>`
3. Run `/set-region <your_desired_region>` (default: us-east-1)
4. Run `/commands` to explore all supported commands

## How the Bot Interacts with AWS Accounts

- Each user configures their own AWS IAM Role using `/setup-role <arn>`.
- The role is stored temporarily in `roles.json` linked with Discord channel + user ID.
- When a user runs a command, the bot looks up their IAM Role and AWS region.
- It uses `boto3` and AWS STS (`assume_role`) to obtain **temporary security credentials**.
- These credentials are used to create short-lived AWS service clients.
- All operations (start/stop/list/metrics) are performed using these temporary scoped credentials.

---

<div style="text-align: center; margin-top: 40px; padding: 20px; background-color: #f8f9fa; border-radius: 8px;">
    <h3>📁 Download Instructions</h3>
    <p>To download this README file:</p>
    <ol style="text-align: left; display: inline-block;">
        <li>Click the download button above this artifact</li>
        <li>Save as <code>README.md</code></li>
        <li>Upload to your GitHub repository root directory</li>
    </ol>
    <p><strong>Or copy the content above and paste it into a new file named <code>README.md</code></strong></p>
</div>