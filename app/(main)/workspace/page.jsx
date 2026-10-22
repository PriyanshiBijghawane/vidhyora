import { WorkspaceClient } from "@/components/WorkspaceClient";
import { getWorkspaceUser, getWorkspaceById } from "@/actions/workspace";

export default async function WorkspacePage({ searchParams }) {
  const { prompt, id } = await searchParams;

  const user = await getWorkspaceUser();

  let workspace = null;
  let workspaceError = null;

  if (id) {
    const result = await getWorkspaceById(id, user.id);
    if (result && typeof result === "object" && "workspace" in result) {
      workspace = result.workspace;
      if (result.error) {
        workspaceError = {
          code: result.error,
          message: result.errorMessage,
        };
      }
    } else {
      workspace = result;
      if (!workspace) {
        workspaceError = {
          code: "NOT_FOUND",
          message: "Workspace not found.",
        };
      }
    }
  }

  return (
    <WorkspaceClient
      key={id || "new"}
      initialPrompt={prompt ?? null}
      requestedWorkspaceId={id ?? null}
      workspace={workspace}
      workspaceError={workspaceError}
      userCredits={user.credits}
      userId={user.id}
      userPlan={user.plan}
    />
  );
}
