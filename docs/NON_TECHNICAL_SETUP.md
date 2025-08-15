# 🏦 Step-by-Step Setup for Non-Technical Users

**Don't worry!** You don't need any programming knowledge. This guide will walk you through getting your own financial management app in just **10-15 minutes**.

---

## 🎯 **What You'll Get**
- Your own personal financial management website
- Secure Google login
- Option to connect bank accounts later
- Modern, mobile-friendly interface
- Professional-grade security

**Cost: ~$1-5 per month** (we'll set up automatic budget alerts)

---

## 📋 **What You Need Before Starting**
- ✅ A Google account (Gmail)
- ✅ A credit card (for Google Cloud - you won't be charged much)
- ✅ 10-15 minutes of your time
- ✅ A computer with internet

---

## 🚀 **Step 1: Get Your Google OAuth Keys (Required - 3 minutes)**

This allows users to log in with their Google accounts.

1. **Go to** [https://console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)

2. **Click "Create Credentials"** → **"OAuth 2.0 Client ID"**

3. **If prompted**, configure OAuth consent screen:
   - Application name: "My Financial App"
   - User support email: Your email
   - Click "Save and Continue" through all steps

4. **Create OAuth Client:**
   - Application type: **"Web application"**
   - Name: "Financial App Client"
   - Click "Create"

5. **Copy these values** (keep them safe):
   - **Client ID**: Looks like `123456789-abc123.apps.googleusercontent.com`
   - **Client Secret**: Looks like `GOCSPX-abc123def456ghi789`

💡 **Keep these 2 values handy** - you'll need them in Step 3!

---

## 🚀 **Step 2: Start the One-Click Deployment**

1. **Click this button** (it will open a new tab):

   [![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/sundeep-dayalan/sage-financial-management.git&cloudshell_open_in_editor=cloudshell/one-click-deploy.sh&cloudshell_tutorial=docs/CLOUD_SHELL_TUTORIAL.md)

2. **Sign in to Google** if prompted

3. **Accept Google Cloud Shell terms** if shown

4. **Wait** for Cloud Shell to load (about 30 seconds)

You'll see a black terminal window - don't worry, this is normal!

---

## 🚀 **Step 3: Run the Magic Script**

1. **Look for the "Run" button** (▶️) at the top of the screen

2. **Click "Run"** - this starts the automatic setup

3. **Follow the colorful prompts** that appear:

### **You'll see this welcome screen:**
```
    ███████╗ █████╗  ██████╗ ███████╗
    ██╔════╝██╔══██╗██╔════╝ ██╔════╝
    ███████╗███████║██║  ███╗█████╗  
    ╚════██║██╔══██║██║   ██║██╔══╝  
    ███████║██║  ██║╚██████╔╝███████╗
    ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
    
    FINANCIAL MANAGEMENT APP
    One-Click GCP Deployment
```

### **When asked for billing account:**
- You'll see a list of your billing accounts
- **Type the ID** of the one you want to use
- If you don't have one, **create it first** at [https://console.cloud.google.com/billing](https://console.cloud.google.com/billing)

### **When asked for Google OAuth credentials (Required):**
**Enter the 2 values** you saved from Step 1:

```
Google OAuth Setup (Required):
Enter Google OAuth Client ID: [paste your Google OAuth Client ID]
Enter Google OAuth Client Secret: [paste your Google OAuth Client Secret]
```

### **When asked about Plaid (Optional):**
You'll see:
```
Plaid Setup (Optional):
Do you want to set up Plaid integration now? [y/N]:
```

**You have two choices:**

**Option A: Skip for now (Recommended for beginners)**
- Type: **N** and press Enter
- You can set up bank connections later in the app
- Your app will work without this

**Option B: Set up bank integration now**
- Type: **y** and press Enter
- You'll need to get Plaid credentials first:
  1. Go to [dashboard.plaid.com](https://dashboard.plaid.com/)
  2. Sign up → Create Application
  3. Copy Client ID and Secret

### **GitHub Integration (Optional):**
- If you want automatic updates: Say **"y"** and provide GitHub details
- If you just want the app: Say **"n"**

---

## 🎉 **Step 4: Watch the Magic Happen (8-10 minutes)**

You'll see lots of colorful text showing progress:

```
🔵 [INFO] Creating new Google Cloud project...
✅ [SUCCESS] Project created: sage-financial-1673925847-4829
🔵 [INFO] Enabling required APIs...
✅ [SUCCESS] All APIs enabled
🔵 [INFO] Deploying infrastructure...
✅ [SUCCESS] Infrastructure deployed
🔵 [INFO] Building and deploying backend...
✅ [SUCCESS] Backend deployed to Cloud Run
🔵 [INFO] Building and deploying frontend...
✅ [SUCCESS] Frontend deployed to Firebase
```

**Don't close the window!** Let it finish completely.

---

## 🎊 **Step 5: Success! Your App is Ready**

When finished, you'll see:

```
🎉 DEPLOYMENT COMPLETED!

Your Sage Financial Management App is ready!

📊 Project Details:
   Project ID: sage-financial-1673925847-4829
   Region: us-central1

🌐 Application URLs:
   Frontend: https://sage-financial-1673925847-4829.web.app
   Backend: https://sage-backend-xxx-uc.a.run.app

💰 Cost Management:
   ✅ Budget alert set for $10/month
   ✅ Billing notifications enabled
```

**Copy your Frontend URL** - this is your personal financial app!

---

## 🔧 **Step 6: Final Setup (1 minute)**

### **Update OAuth Settings:**

1. **Go back to** [https://console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials)

2. **Find your OAuth Client** and click the pencil (✏️) to edit

3. **Scroll to "Authorized redirect URIs"**

4. **Click "Add URI"** and add:
   - `https://YOUR-FRONTEND-URL/auth/callback`
   - (Replace YOUR-FRONTEND-URL with your actual URL from Step 5)

5. **Click "Save"**

---

## 🎯 **Step 7: Test Your App**

1. **Open your Frontend URL** in a new tab

2. **Click "Sign in with Google"**

3. **Explore your new financial app!**

---

## 🏦 **Step 8: Set Up Bank Connections (Optional)**

If you skipped Plaid setup in Step 3, you can add it later:

### **Option A: Use the App Interface (Easiest)**
1. **In your app**, look for "Settings" or "Connect Bank Account"
2. **Follow the prompts** to enter your Plaid credentials
3. **The app will guide you** through the setup

### **Option B: Get Plaid Credentials**
1. **Go to** [https://dashboard.plaid.com/](https://dashboard.plaid.com/)
2. **Sign up** → Create Application
3. **Copy your credentials** and use them in the app

### **Test Bank Account:**
- Bank: "First Platypus Bank"
- Username: `user_good`
- Password: `pass_good`

---

## 🛡️ **What You've Got**

### **Your Personal Financial App:**
- ✅ **Secure login** with your Google account
- ✅ **Professional website** on your own domain
- ✅ **Mobile-friendly design**
- ✅ **Enterprise-grade security**
- ✅ **Option to add bank accounts** anytime

### **Automatic Monitoring:**
- ✅ **$10/month budget alerts** (you'll get emails if costs exceed this)
- ✅ **Uptime monitoring** (you'll know if your app goes down)
- ✅ **Security scanning** (automatic protection)

### **Your URLs:**
- **Your App**: `https://your-project-id.web.app`
- **Admin Panel**: `https://console.cloud.google.com/`
- **Cost Monitoring**: `https://console.cloud.google.com/billing`

---

## 💰 **Cost Breakdown**

**What you'll pay monthly:**
- Cloud Run (backend): $0-3
- Firebase Hosting (frontend): $0 (free)
- Firestore (database): $1-2
- Secret Manager: $0.06
- **Total: ~$1-5 per month**

**Budget alerts set at $10/month** - you'll get email warnings at $5, $9, and $10.

---

## 🎉 **Congratulations!**

You've successfully deployed your own financial management platform! 

**You now have:**
- ✅ Your own personal finance website
- ✅ Secure Google authentication
- ✅ Professional-grade infrastructure
- ✅ Automatic cost monitoring
- ✅ Enterprise-level security
- ✅ Option to add bank accounts anytime

**No programming knowledge required!** 🎊

---

## 🚀 **Next Steps**

**Add bank connections:**
- Use the setup guide in your app
- Connect multiple accounts
- Track spending automatically

**Customize your app:**
- Change colors and branding
- Set up spending categories
- Create financial goals

**Share with family:**
- Each person needs their own Google account
- They can use the same app URL
- Data is kept separate and secure

**Monitor costs:**
- Check [billing dashboard](https://console.cloud.google.com/billing) monthly
- You'll get automatic email alerts
- Most usage stays under $5/month

**Happy financial managing!** 💰📊

---

## 🆘 **If Something Goes Wrong**

### **Common Issues:**

**"Permission denied" error:**
- Make sure you're logged into the right Google account
- Ensure billing is enabled on your account

**"OAuth redirect error" when testing:**
- Double-check you added the correct redirect URI in Step 6
- Make sure the URL exactly matches (including https://)

**App doesn't load:**
- Wait 2-3 minutes after deployment
- Try refreshing the page
- Check if you're using the correct URL

### **Need Help?**
1. **Check the logs** in the Cloud Shell window
2. **Try running the script again** (it's safe to re-run)
3. **Contact support** via GitHub issues

The beauty of this setup is that **Plaid is completely optional** - users can get a working financial management app immediately and add bank integrations later when they're ready!