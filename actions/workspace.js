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
  let workspace = null;
  try {
    workspace = await db.workspace.findUnique({
      where: { id: workspaceId, userId },
      select: {
        id: true,
        title: true,
        messages: true,
        fileData: true,
      },
    });
  } catch (err) {
    console.error("Failed to query workspace:", err);
  }

  return workspace;
}
