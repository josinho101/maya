import { Breadcrumbs, Link as MuiLink, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

export interface BreadcrumbSegment {
  label: string;
  to?: string;
}

interface AppBreadcrumbsProps {
  segments: BreadcrumbSegment[];
}

export default function AppBreadcrumbs({ segments }: AppBreadcrumbsProps) {
  return (
    <Breadcrumbs sx={{ mb: 2 }}>
      {segments.map((segment, index) =>
        segment.to ? (
          <MuiLink key={index} component={RouterLink} to={segment.to} underline="hover" color="inherit">
            {segment.label}
          </MuiLink>
        ) : (
          <Typography key={index} color="text.primary">
            {segment.label}
          </Typography>
        ),
      )}
    </Breadcrumbs>
  );
}
