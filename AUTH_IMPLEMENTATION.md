# Magic Link Authentication Implementation Guide

## Overview

This implementation adds **Magic Link Authentication** to TalentFlow, providing a secure, passwordless login/signup experience using email verification.

## Features

✅ **Magic Link Authentication** - Passwordless login via email links
✅ **User Management** - Create users automatically on first login
✅ **JWT Tokens** - Secure session tokens with 7-day expiration
✅ **Profile Management** - Users can update their profile information
✅ **Pipeline Integration** - Link pipelines to authenticated users
✅ **Protected Routes** - Authentication required for app pages
✅ **Email Support** - Development console output + production SMTP

## Architecture

### Backend (Python/FastAPI)

**New Models:**
- `User` - User accounts with email and profile
- `MagicLink` - One-time use email verification tokens

**New Endpoints:**
- `POST /api/auth/send-magic-link` - Send login link to email
- `POST /api/auth/verify` - Verify token and return JWT
- `GET /api/auth/me` - Get current user info
- `PUT /api/auth/profile` - Update user profile
- `POST /api/auth/logout` - Logout endpoint

### Frontend (SvelteKit)

**New Stores:**
- `auth.ts` - Centralized auth state management

**New Pages:**
- `/auth/login` - Magic link request form
- `/auth/verify` - Link verification & token exchange
- `/app/profile` - User profile management
- `/app/my-pipelines` - User's pipelines
- `/app/dashboard` - Authenticated dashboard

## Setup Instructions

### 1. Backend Setup

**Update dependencies:**
```bash
cd server
pip install -e .
```

New packages added:
- `pyjwt` - JWT token generation
- `python-jose` - Token library
- `aiosmtplib` - Async SMTP
- `email-validator` - Email validation
- `bcrypt` - Password hashing (future use)

**Database schema:**
The app automatically creates the `User` and `MagicLink` tables on startup.

**Environment variables:**
Add to `.env`:
```bash
SECRET_KEY=your-secret-key-change-in-production
FRONTEND_BASE_URL=http://localhost:3000

# Optional: SMTP for production email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@talentflow.dev
```

### 2. Frontend Setup

**Install Svelte dependencies:**
```bash
cd frontend
npm install
```

**Configure API base URL:**
Update `.env.local`:
```bash
VITE_API_URL=http://localhost:9002
```

## Usage Flow

### User Login Flow

1. User visits `/auth/login`
2. Enters email address
3. Backend generates unique token and stores in `MagicLink` table
4. Email sent with link: `http://localhost:3000/auth/verify?token=<token>`
5. User clicks link → `/auth/verify` page
6. Frontend verifies token with backend
7. Backend returns JWT access token
8. User stored in `User` table (if new user)
9. Client redirected to `/app` (authenticated area)

### Protected Routes

All `/app/*` routes require authentication:
- Check if token exists in localStorage
- Display login page if not authenticated
- Use token for API requests

### API Integration

Every request to protected endpoints includes:
```javascript
headers: {
  'Authorization': 'Bearer <access_token>'
}
```

## Email Configuration

### Development (Default)

Magic links are printed to console:
```
[MAGIC LINK EMAIL]
To: user@example.com
Subject: Your TalentFlow Login Link

Welcome to TalentFlow
Click the link below to log in...
http://localhost:3000/auth/verify?token=...
```

### Production

Configure SMTP in environment:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@talentflow.dev
```

## User & Pipeline Integration

### Connecting Users to Pipelines

Update the existing pipeline model to include `user_id`:

```python
class Pipeline(Base):
    __tablename__ = "pipelines_v2"
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped[User] = relationship("User")
```

### Fetching User's Pipelines

```python
@router.get("/api/pipelines-v2/my-pipelines")
async def get_user_pipelines(
    db: Session = Depends(get_db),
    token: str = Depends(get_token_from_header)
):
    user_id = decode_token(token)
    pipelines = db.query(Pipeline).filter(Pipeline.user_id == user_id).all()
    return pipelines
```

## Testing

### Manual Testing

1. Start backend: `cd server && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Visit `http://localhost:3000/auth/login`
4. Enter test email
5. Check console for magic link
6. Click link in console output
7. Should redirect to dashboard

### API Testing with curl

**Send magic link:**
```bash
curl -X POST http://localhost:9002/api/auth/send-magic-link \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'
```

**Verify token:**
```bash
curl -X POST http://localhost:9002/api/auth/verify \
  -H "Content-Type: application/json" \
  -d '{"token":"<token-from-email>"}'
```

**Get current user:**
```bash
curl -X GET http://localhost:9002/api/auth/me \
  -H "Authorization: Bearer <access_token>"
```

## Security Considerations

1. **Magic Link Expiration** - Links expire in 15 minutes
2. **One-Time Use** - Tokens can only be used once
3. **JWT Expiration** - Access tokens valid for 7 days
4. **HTTPS Required** - Use HTTPS in production
5. **CORS** - Currently allows all origins (restrict in production)
6. **SECRET_KEY** - Must be changed in production
7. **Email Verification** - Links only valid once, preventing replay attacks

## File Structure

```
server/
  app/
    models.py          # Added User, MagicLink models
    routers/
      auth.py          # New auth endpoints
    main.py            # Added auth router

frontend/
  src/
    stores/
      auth.ts          # Auth state management
    routes/
      auth/
        login/
          +page.svelte # Login form
        verify/
          +page.svelte # Link verification
      app/
        profile/
          +page.svelte # User profile
        my-pipelines/
          +page.svelte # User pipelines
        dashboard/
          +page.svelte # Dashboard
```

## Next Steps

1. **Database User-Pipeline Relationship** - Add `user_id` foreign key to pipelines
2. **Email Templates** - Customize email HTML
3. **API Docs** - Each endpoint has Swagger docs at `/docs`
4. **Rate Limiting** - Add rate limiting for auth endpoints
5. **Audit Logging** - Track login attempts and actions
6. **Two-Factor Auth** - Optional 2FA support
7. **Social Login** - Google/GitHub OAuth integration

## Branch Information

This implementation is on the `new0` branch. To merge to main:

```bash
git checkout main
git merge new0
```

## Support

For issues or questions:
- Check endpoint documentation at `/docs` when API is running
- Review environment variables in `.env.example`
- Check browser console for frontend errors
- Check server logs for backend errors
