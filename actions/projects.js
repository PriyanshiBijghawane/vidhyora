"use server";

import { auth } from "@clerk/nextjs/server";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { db } from "@/lib/prisma";
import { checkUser } from "@/lib/checkUser";

// ─── Get all workspaces for the current user ──────────────────────────────────

export async function getUserProjects() {
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
      select: { id: true },
    });
  } catch (err) {
    console.error("Failed to query user for projects:", err);
  }

  if (!user) {
    try {
      const checkedUser = await checkUser();
      if (checkedUser) {
        user = { id: checkedUser.id };
      }
    } catch (err) {
      console.error("Failed to check/create user for projects:", err);
    }
  }

  if (!user) return [];

  try {
    const workspaces = await db.workspace.findMany({
      where: { userId: user.id },
      select: {
        id: true,
        title: true,
        createdAt: true,
        updatedAt: true,
        messages: true,
      },
      orderBy: { updatedAt: "desc" },
    });

    if (!Array.isArray(workspaces)) return [];

    return workspaces.map((w) => {
      let msgs = [];
      if (Array.isArray(w.messages)) {
        msgs = w.messages;
      } else if (typeof w.messages === "string") {
        try {
          const parsed = JSON.parse(w.messages);
          if (Array.isArray(parsed)) msgs = parsed;
        } catch {
          msgs = [];
        }
      }

      const firstUserMsg = msgs.find(
        (m) =>
          typeof m === "object" &&
          m !== null &&
          m.role === "user"
      );

      let firstPrompt = null;
      if (firstUserMsg && typeof firstUserMsg.content === "string") {
        firstPrompt = firstUserMsg.content.slice(0, 120);
      } else if (firstUserMsg && firstUserMsg.content != null) {
        firstPrompt = String(firstUserMsg.content).slice(0, 120);
      }

      return {
        id: w.id,
        title: w.title ?? "Untitled project",
        firstPrompt,
        createdAt: w.createdAt ? new Date(w.createdAt).toISOString() : new Date().toISOString(),
        updatedAt: w.updatedAt ? new Date(w.updatedAt).toISOString() : new Date().toISOString(),
        messageCount: msgs.length,
      };
    });
  } catch (err) {
    console.error("Failed to fetch workspaces:", err);
    return [];
  }
}

// ─── Delete a workspace ───────────────────────────────────────────────────────

export async function deleteProject(workspaceId) {
  if (!workspaceId) return;

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
      select: { id: true },
    });
  } catch (err) {
    console.error("Failed to query user for deleteProject:", err);
  }

  if (!user) return;

  try {
    await db.workspace.deleteMany({
      where: { id: workspaceId, userId: user.id },
    });
  } catch (err) {
    console.error("Failed to delete workspace:", err);
    throw err;
  }

  revalidatePath("/projects");
}
