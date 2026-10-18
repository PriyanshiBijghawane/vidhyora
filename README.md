# Vidhyora — AI-Powered Workspace

Vidhyora is an AI-powered development workspace that helps users generate, edit, preview, and improve React applications using AI.

Build applications from natural-language prompts, explore generated code, and preview changes in an interactive workspace.

##  Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Authentication](#auth-clerk)
- [Workspace](#workspace)
- [AI Code Generation](#ai-code-generation-api-gen-ai-code)
- [Improve with AI](#improve-with-ai--cline-sdk-api-improve--pro--starter)
- [Fix with AI](#fix-with-ai)
- [Code Panel](#code-panel-sandpack)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)

---

## Overview

Vidhyora is an AI-powered development workspace designed to simplify React application development.

Users can describe their application requirements in natural language and use AI to generate code. The workspace brings together chat, code editing, and live preview to make application development easier.

The project is designed around an interactive development workflow, with features such as AI-assisted code generation, workspace management, code preview, and AI-powered code improvement.

Vidhyora aims to provide a convenient environment where developers can experiment with ideas, inspect generated code, and iteratively improve their applications.

---

## Tech Stack

## Tech Stack

| Layer | Technology |

| Frontend Framework | Next.js |
| UI Library | React |
| Language | JavaScript |
| Styling | Tailwind CSS |
| Authentication | Clerk |
| Database ORM | Prisma |
| Backend API | FastAPI |
| AI Integration | Gemini |
| Code Editor | Monaco Editor |
| Live Code Preview | Sandpack |
| Icons | Lucide React |
| Notifications | Sonner |
---

## Features

### Landing Page

- Prompt input for describing the application to generate
- Suggestion chips to help users get started
- Overview of available features and workflow
- Pricing information through Clerk's `<PricingTable />` component, if configured

- 
### Authentication (Clerk)

- User authentication using Clerk
- Google OAuth sign-in, if configured
- User account integration with the application's database
- Subscription and plan management, if implemented
- Access to account-related features through authenticated sessions

### Workspace

- Split-panel workspace for chat and code preview
- AI-assisted application development through chat
- Code and preview tabs for inspecting generated applications
- Workspace history, if persistence is implemented
- Image upload support, if configured
- User avatars and automatic scrolling, if implemented

### AI Code Generation

- Generate application code from natural-language prompts
- AI-assisted React application development
- Display generated code in the workspace
- Preview generated applications using Sandpack
- Handle AI responses and generated files through the backend API

### Improve with AI

- Use AI to improve existing application code
- Update files based on user instructions
- Review generated changes in the code workspace
- Preview updated code to evaluate the result

These capabilities depend on the AI improvement workflow being configured and implemented in the project.

### Fix with AI

- Identify runtime or compilation errors in the application preview
- Provide error context to the AI for troubleshooting
- Generate suggested fixes based on the reported error
- Preview the updated code after applying a fix

Error detection and AI-assisted fixes depend on the corresponding functionality being implemented in the project.

### Code Panel

- Switch between Code and Preview tabs
- Inspect generated application files
- Preview React applications in an interactive browser environment
- View code changes as the application is updated
- Use Sandpack for the live preview, if configured

  ### Projects Page

- Display saved workspaces in a grid
- Show workspace titles and prompt previews
- Display message counts and timestamps
- Delete workspaces with a confirmation dialog
- Show an empty state with a call to action for new users

### Token / Credit System

- Credit-based usage system for AI operations
- Free, Starter, and Pro subscription plans
- Credit deduction for code generation and AI improvements
- Credit balance validation before processing requests
- Credit updates based on subscription plan changes

---

## Getting Started

### Prerequisites

Before running Vidhyora, make sure you have installed:

- Node.js and npm
- Python (if running the FastAPI backend)
- Git

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/PriyanshiBijghawane/vidhyora.git
   ```

2. Open the project directory:

   ```bash
   cd vidhyora
   ```

3. Install frontend dependencies:

   ```bash
   npm install
   ```

4. Configure the required environment variables.

5. Start the frontend development server:

   ```bash
   npm run dev
   ```

Open `http://localhost:3000` in your browser.

### Backend

If your project uses the FastAPI backend, follow these steps from the backend directory:

1. Create and activate a Python virtual environment.
2. Install the dependencies listed in your backend requirements file.
3. Configure the backend environment variables.
4. Start the FastAPI server using your project's configured command.

---

## Environment Variables

Vidhyora uses environment variables to configure authentication, database access, and AI services.

### Frontend Environment

Create a `.env` file in the project root and add the variables required by your application.

```env
# Clerk Authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=

# Database
DATABASE_URL=

# Gemini AI
GEMINI_API_KEY=

# Arcjet (if configured)
ARCJET_KEY=
```
---

### Setup Notes

- Get credentials from the relevant service dashboards.
- Add only the environment variables required by your actual project configuration.
- Never commit real API keys, passwords, or database credentials to GitHub.
- Keep local `.env` files out of version control.
- Restart the development server after changing environment variables.

Check the project's configuration files to confirm the exact variable names required.

---

## Database Setup

Vidhyora uses a database to store user information and workspace data, depending on the configured backend.

### Database Configuration

- Configure the database connection using the appropriate environment variables.
- Apply the Prisma schema and migrations if Prisma is configured.
- Ensure the database is accessible before starting the application.

### Data Models

Document the models defined in your current Prisma schema here, including their fields and relationships.

### Image Storage

If image uploads are enabled, configure the required storage provider and bucket permissions according to the application settings.

## 🌟 Show Your Support

If you find Vidhyora useful, consider giving this repository a ⭐ on GitHub!
    

