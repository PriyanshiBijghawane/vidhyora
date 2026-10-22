"use server";

import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { db } from "@/lib/prisma";
import { checkUser } from "@/lib/checkUser";

// ─── Get the current authenticated user ──────────────────────────────────────

export async function getWorkspaceUser() {
  let clerkId = null;
  try {
    const authData = await auth();
    clerkId = authData?.userId;
  } catch (err) {
    if (err && err.digest?.startsWith("NEXT_REDIRECT")) throw err;
  }
  if (!clerkId) redirect("/");

  let user = null;
  try {
    user = await db.user.findUnique({
      where: { clerkId },
      select: { id: true, credits: true, plan: true },
    });
  } catch (err) {
    console.error("Failed to query user in getWorkspaceUser:", err);
  }

  if (!user) {
    try {
      const checkedUser = await checkUser();
      if (checkedUser) {
        user = {
          id: checkedUser.id,
          credits: checkedUser.credits,
          plan: checkedUser.plan,
        };
      }
    } catch (err) {
      console.error("Failed to check/create user in getWorkspaceUser:", err);
    }
  }

  if (!user && clerkId) {
    user = {
      id: clerkId,
      credits: 10,
      plan: "free",
    };
  }

  if (!user) redirect("/");

  return user;
}

// ─── Get a workspace by id (must belong to the current user) ─────────────────

export async function getWorkspaceById(workspaceId, userId) {
  if (!workspaceId) return { workspace: null, error: null };
  try {
    const workspace = await db.workspace.findFirst({
      where: {
        id: workspaceId,
        ...(userId
          ? {
              OR: [
                { userId },
                { user: { clerkId: userId } },
                { user: { id: userId } },
              ],
            }
          : {}),
      },
      select: {
        id: true,
        title: true,
        messages: true,
        fileData: true,
        userId: true,
      },
    });

    if (!workspace) {
      // Check whether workspace exists under another user to distinguish unauthorized from not found
      const existing = await db.workspace.findUnique({
        where: { id: workspaceId },
        select: { id: true, userId: true },
      });

      if (existing) {
        return {
          workspace: null,
          error: "UNAUTHORIZED",
          errorMessage: "You do not have permission to access this workspace.",
        };
      }

      return {
        workspace: null,
        error: "NOT_FOUND",
        errorMessage: "Workspace not found.",
      };
    }

    return { workspace, error: null };
  } catch (err) {
    console.error("Failed to query workspace:", err);
    return {
      workspace: null,
      error: "DATABASE_ERROR",
      errorMessage:
        "Could not load workspace due to a database connection error. Please refresh to try again.",
    };
  }
}
