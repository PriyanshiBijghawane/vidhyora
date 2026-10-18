import re
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("backend.sanitizer")

FORBIDDEN_DEPS = {
    "@clerk/clerk-react",
    "@clerk/nextjs",
    "@clerk/clerk-sdk-node",
    "@clerk/express",
    "@clerk/backend",
    "@supabase/supabase-js",
    "firebase",
    "firebase-admin"
}

MOCK_CLERK_HEADER = """
// Mock Clerk authentication for Sandpack browser preview
const useUser = typeof window !== 'undefined' && window.useUser ? window.useUser : () => ({ isSignedIn: true, user: { fullName: "Demo User", firstName: "Demo", primaryEmailAddress: { emailAddress: "demo@example.com" }, imageUrl: "" } });
const useClerk = typeof window !== 'undefined' && window.useClerk ? window.useClerk : () => ({ signOut: () => alert("Logged out successfully"), openUserProfile: () => alert("Profile Opened"), openSignIn: () => {}, openSignUp: () => {} });
const ClerkProvider = ({ children }) => <>{children}</>;
const SignedIn = ({ children }) => <>{children}</>;
const SignedOut = ({ children }) => null;
const UserButton = () => <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center font-bold text-xs shadow cursor-pointer">U</div>;
"""

def sanitize_code_and_files(files: Dict[str, Any], dependencies: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    cleaned_deps = {k: v for k, v in (dependencies or {}).items() if k not in FORBIDDEN_DEPS}
    cleaned_files = {}

    for path, f_data in (files or {}).items():
        if isinstance(f_data, dict):
            code = f_data.get("code", "")
        else:
            code = getattr(f_data, "code", "")

        if not isinstance(code, str):
            code = str(code)

        # 1. Replace import.meta.env and import.meta
        code = re.sub(r"\bimport\.meta\.env\b", "(typeof process !== 'undefined' && process.env ? process.env : {})", code)
        code = re.sub(r"\bimport\.meta\b", "{}", code)

        # 2. Check for @clerk imports
        if "@clerk/" in code:
            logger.info(f"Sanitizing @clerk import in {path}")
            code = re.sub(r"import\s+.*?from\s+['\"]@clerk/.*?['\"];?\n?", "", code)
            if "useUser" in code or "useClerk" in code or "UserButton" in code or "ClerkProvider" in code:
                if "const useUser =" not in code:
                    code = MOCK_CLERK_HEADER.strip() + "\n\n" + code

        # 3. Check for @supabase imports
        if "@supabase/" in code:
            logger.info(f"Sanitizing @supabase import in {path}")
            code = re.sub(r"import\s+.*?from\s+['\"]@supabase/.*?['\"];?\n?", "", code)

        # 4. Check for firebase imports
        if "firebase/" in code:
            logger.info(f"Sanitizing firebase import in {path}")
            code = re.sub(r"import\s+.*?from\s+['\"]firebase/.*?['\"];?\n?", "", code)

        cleaned_files[path] = {"code": code}

    return cleaned_files, cleaned_deps
