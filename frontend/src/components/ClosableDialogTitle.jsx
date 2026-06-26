import { DialogTitle, IconButton } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";

export default function ClosableDialogTitle({ onClose, children, sx, ...props }) {
  return (
    <DialogTitle sx={{ pr: 6, ...sx }} {...props}>
      {children}
      <IconButton
        aria-label="close"
        onClick={onClose}
        size="small"
        sx={{ position: "absolute", right: 12, top: 12, color: "text.secondary" }}
      >
        <CloseIcon fontSize="small" />
      </IconButton>
    </DialogTitle>
  );
}
