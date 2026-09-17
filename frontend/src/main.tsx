import { StrictMode, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { LearningDashboard } from "./LearningDashboard";
import { ProblemExplorer } from "./ProblemExplorer";
import { ContestExplorer } from "./ContestExplorer";
import { ProblemList } from "./ProblemList";
import { Dashboard } from "./Dashboard";
import { theme } from "./theme";
import type {
  ContestExplorerData,
  DashboardData,
  LearningContentData,
  LearningContentStat,
  ProblemListData
} from "./types";

function readJson<T>(elementId: string): T {
  const element = document.getElementById(elementId);
  if (!element?.textContent) throw new Error(`Missing JSON data: ${elementId}`);
  return JSON.parse(element.textContent) as T;
}

function render(element: HTMLElement, component: ReactNode) {
  createRoot(element).render(
    <StrictMode>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {component}
      </ThemeProvider>
    </StrictMode>
  );
}

const dashboardRoot = document.getElementById("learning-dashboard-root");
if (dashboardRoot) {
  render(
    dashboardRoot,
    <LearningDashboard items={readJson<LearningContentStat[]>("learning-dashboard-data")} />
  );
}

const explorerRoot = document.getElementById("problem-explorer-root");
if (explorerRoot) {
  render(
    explorerRoot,
    <ProblemExplorer
      data={readJson<LearningContentData>("problem-explorer-data")}
      csrfToken={explorerRoot.dataset.csrfToken ?? ""}
    />
  );
}

const contestExplorerRoot = document.getElementById("contest-explorer-root");
if (contestExplorerRoot) {
  render(
    contestExplorerRoot,
    <ContestExplorer
      data={readJson<ContestExplorerData>("contest-explorer-data")}
      csrfToken={contestExplorerRoot.dataset.csrfToken ?? ""}
    />
  );
}

const problemListRoot = document.getElementById("problem-list-root");
if (problemListRoot) {
  render(
    problemListRoot,
    <ProblemList
      data={readJson<ProblemListData>("problem-list-data")}
      csrfToken={problemListRoot.dataset.csrfToken ?? ""}
    />
  );
}

const dashboardRootElement = document.getElementById("dashboard-root");
if (dashboardRootElement) {
  render(
    dashboardRootElement,
    <Dashboard
      data={readJson<DashboardData>("dashboard-data")}
      csrfToken={dashboardRootElement.dataset.csrfToken ?? ""}
    />
  );
}
