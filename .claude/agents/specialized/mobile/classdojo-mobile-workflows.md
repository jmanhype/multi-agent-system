# ClassDojo Mobile Parent Account Workflows

## Device Setup
- **Device**: Android Emulator (emulator-5554)
- **App**: ClassDojo Android (com.classdojo.android)
- **Status**: App pre-installed and functional

## 1. Authentication/Login Flow

### Login Screen Components
- **Email/Username field** (ID: fragment_login_et_username)
- **Password field** (ID: fragment_login_et_password) 
- **"Forgot your password?" link** (ID: nessie_button_text_view)
- **"Log in" button** (ID: nessie_button_text_view)
- **"Continue with Google" button** (Google SSO option)
- **Navigate up button** (back navigation)

### Authentication Options
1. **Email/Password Login**: Traditional credentials
2. **Google SSO**: Single sign-on with Google account
3. **Password Recovery**: "Forgot your password?" link (requires email entry first)

### Screen Layout
- Clean, minimal design with purple accent colors
- Input fields with rounded borders
- Clear visual hierarchy with "OR" divider between login methods
- Standard mobile UX patterns

## 2. Registration/Signup Flow

### Signup Screen Components
- **ClassDojo house icon** (brand identifier)
- **"Enter your email address" header**
- **"Already have an account? Log in" link** (navigation back to login)
- **Email address input field**
- **"Continue" button** (primary CTA)
- **Terms of Service link** (purple text)
- **Privacy Policy link** (purple text)
- **"Continue with Google" button** (alternative registration method)

### Registration Options
1. **Email Registration**: Traditional email-based account creation
2. **Google SSO Registration**: Account creation via Google
3. **Legal Compliance**: Clear presentation of Terms and Privacy Policy

### User Flow Navigation
- **Login ↔ Signup**: Easy navigation between authentication modes
- **Legal Documents**: Accessible Terms of Service and Privacy Policy
- **Consistent Design**: Same visual language as login screen

## 3. User Role Selection & Onboarding Flow

### App Launch - Role Selection Screen
- **App Brand**: "Happier Classrooms" with ClassDojo mascot
- **User Types Available**:
  - 🏠 **"I'm a parent"** (house icon)
  - ❤️ **"I'm a teacher"** (heart icon)
  - 🎒 **"I'm a student"** (backpack icon)
  - 🏆 **"I'm a school leader"** (trophy icon)
- **Secondary Action**: "Log in" button (top-right corner)

### Parent-Specific Flow
**Selection**: "I'm a parent" → **Parent Registration Screen**
- Same design as general signup but contextually relevant
- Clear path for parent account creation
- Consistent with overall app UX patterns

## 4. Complete Parent User Journey Map

### Entry Points
1. **Fresh App Launch** → Role Selection → Parent Registration
2. **Returning User** → "Log in" → Authentication Screen
3. **Role Switching** → Back navigation → Role Selection

### Authentication Flows
1. **New Parent Registration**:
   - Role Selection → Email Registration → Account Setup
   - Alternative: Role Selection → Google SSO Registration
2. **Existing Parent Login**:
   - Direct login → Email/Password → Parent Dashboard
   - Alternative: Direct login → Google SSO → Parent Dashboard

### Navigation Architecture
- **Role Selection** ⇄ **Login Screen** (bidirectional)
- **Role Selection** → **Parent Registration** → **Parent Dashboard**
- **Login Screen** → **Password Recovery** → **Email Verification**

## Exploration Progress
✅ Initial app launch and login screen analysis  
✅ Google SSO flow tested (redirects to Google auth)
✅ Password recovery flow explored (requires email first)
✅ Signup/registration workflow discovered
✅ User role selection screen discovered and explored
✅ Parent-specific onboarding flow mapped
✅ Complete parent user journey documented
🔄 Currently finalizing workflow documentation
✅ Legal document access pattern discovered (requires email entry)
✅ Complete parent workflow mapping completed

## 5. Key Insights & Parent Workflow Findings

### Authentication Barriers
- **No Guest/Demo Mode**: Full registration required for access
- **Email-First Pattern**: Legal docs, password recovery require email entry
- **Role-Based Onboarding**: Clear separation of user types from app launch

### Parent-Specific User Experience
- **Dedicated Parent Path**: Role selection leads to parent-optimized flows  
- **Consistent Branding**: House icon represents parent identity throughout
- **Dual Registration Options**: Email-based or Google SSO for parent accounts
- **Legal Compliance**: Clear presentation of Terms of Service and Privacy Policy

### Technical Implementation Notes
- **App Package**: `com.classdojo.android`
- **Platform**: Optimized for Android mobile experience
- **Navigation Patterns**: Standard back navigation, role-based routing
- **Input Validation**: Email-first approach for security features

### Limitations Discovered
- **Authentication Required**: Cannot access dashboard features without valid credentials
- **No Demo Content**: No guest mode or sample parent dashboard available
- **Document Access Gated**: Legal documents require email input first

### Next Steps for Parent Feature Exploration
To fully explore parent features, would need:
1. Valid parent account credentials
2. Associated student/class connections
3. Teacher partnerships for messaging flows
4. Active classroom/school environment

---
*Exploration conducted by Mobile Automation Coordinator*
*Device: Android Emulator | Date: 2025-09-05*