#!/bin/bash

# AWS Credentials Setup Helper
echo "🔐 AWS Credentials Configuration"
echo "================================"
echo ""
echo "For a NEW AWS account, you need to create an IAM user first."
echo ""
echo "📋 Step-by-Step Instructions:"
echo ""
echo "1. Go to AWS Console: https://console.aws.amazon.com"
echo "2. Sign in with your root account (the email you used to create AWS account)"
echo "3. Go to IAM: https://console.aws.amazon.com/iam/"
echo "4. Click 'Users' in the left sidebar"
echo "5. Click 'Create user' button"
echo "6. Enter a username (e.g., 'admin-user' or 'cli-user')"
echo "7. Click 'Next'"
echo "8. Under 'Set permissions', choose 'Attach policies directly'"
echo "9. Search for and select 'AdministratorAccess' (for full access)"
echo "   OR select 'PowerUserAccess' (for most use cases without billing access)"
echo "10. Click 'Next' → 'Create user'"
echo ""
echo "11. Click on the user you just created"
echo "12. Go to 'Security credentials' tab"
echo "13. Scroll down to 'Access keys' section"
echo "14. Click 'Create access key'"
echo "15. Choose 'Command Line Interface (CLI)'"
echo "16. Check the confirmation box and click 'Next'"
echo "17. Optionally add a description tag, then click 'Create access key'"
echo "18. IMPORTANT: Copy BOTH the Access Key ID and Secret Access Key"
echo "    (You won't see the Secret Access Key again!)"
echo ""
echo "⚠️  Security Note: Never share these keys or commit them to git!"
echo ""

read -p "Do you have your AWS Access Key ID and Secret Access Key ready? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please get your credentials first, then run this script again."
    exit 1
fi

echo ""
echo "Now we'll configure AWS CLI. You'll be prompted for:"
echo "- AWS Access Key ID"
echo "- AWS Secret Access Key"
echo "- Default region (recommend: us-east-1 for lowest cost)"
echo "- Default output format (recommend: json)"
echo ""

aws configure

echo ""
echo "✅ AWS credentials configured!"
echo ""
echo "Verifying credentials..."
if aws sts get-caller-identity &> /dev/null; then
    echo "✅ Credentials are valid!"
    aws sts get-caller-identity
else
    echo "❌ Credentials verification failed. Please check your credentials."
    exit 1
fi
