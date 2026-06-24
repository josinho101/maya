export interface NavItem {
  label: string;
  path: string;
}

export function buildProjectNavItems(projectId: string): NavItem[] {
  const base = `/projects/${projectId}`;
  return [
    { label: "Environments", path: `${base}/environments` },
    { label: "Test Cases", path: `${base}/test-cases` },
    { label: "Runs", path: `${base}/runs` },
    { label: "Healing", path: `${base}/healing` },
    { label: "Scenarios", path: `${base}/scenarios` },
    { label: "Notifications", path: `${base}/notifications` },
  ];
}
