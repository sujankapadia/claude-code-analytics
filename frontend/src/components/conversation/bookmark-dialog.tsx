import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { Bookmark } from "@/api/types";

interface BookmarkDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  existing?: Bookmark;
  onSave: (name: string, description: string) => void;
  onDelete: () => void;
}

export function BookmarkDialog({
  open,
  onOpenChange,
  existing,
  onSave,
  onDelete,
}: BookmarkDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    if (open) {
      setName(existing?.name ?? "");
      setDescription(existing?.description ?? "");
    }
  }, [open, existing]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onSave(name.trim(), description.trim());
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {existing ? "Edit Bookmark" : "Bookmark Message"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">
              Name
            </label>
            <Input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Good refactoring approach"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">
              Description (optional)
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Why this message is worth saving..."
              rows={2}
            />
          </div>
          <DialogFooter>
            {existing && (
              <Button
                type="button"
                variant="destructive"
                size="sm"
                onClick={onDelete}
              >
                Remove
              </Button>
            )}
            <Button type="submit" size="sm" disabled={!name.trim()}>
              {existing ? "Update" : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
