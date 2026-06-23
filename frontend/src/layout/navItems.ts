export interface NavItem {
  label: string;
  path: string;
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Projects", path: "/projects" },
  { label: "Test Cases", path: "/test-cases" },
  { label: "Runs", path: "/runs" },
  { label: "Healing", path: "/healing" },
  { label: "Notifications", path: "/notifications" },
];
