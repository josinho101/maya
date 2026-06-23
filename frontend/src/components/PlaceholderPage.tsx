import { Typography } from "@mui/material";

interface PlaceholderPageProps {
  title: string;
}

export default function PlaceholderPage({ title }: PlaceholderPageProps) {
  return <Typography variant="h4">{title}</Typography>;
}
