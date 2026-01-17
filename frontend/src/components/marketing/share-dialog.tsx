"use client";

import { useState, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Copy, Check, ExternalLink } from "lucide-react";
import type { ShareInfo } from "@/hooks/use-marketing-chatkit";

type ShareDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  shareInfo: ShareInfo | null;
  isLoading: boolean;
  onToggleShare: (isShared: boolean) => Promise<void>;
};

export function ShareDialog({
  open,
  onOpenChange,
  shareInfo,
  isLoading,
  onToggleShare,
}: ShareDialogProps) {
  const [copying, setCopying] = useState(false);
  const [toggling, setToggling] = useState(false);

  const shareUrl =
    shareInfo?.share_url && typeof window !== "undefined"
      ? `${window.location.origin}${shareInfo.share_url}`
      : null;

  const handleToggle = useCallback(
    async (checked: boolean) => {
      setToggling(true);
      try {
        await onToggleShare(checked);
      } finally {
        setToggling(false);
      }
    },
    [onToggleShare]
  );

  const handleCopy = useCallback(async () => {
    if (!shareUrl) return;
    setCopying(true);
    try {
      await navigator.clipboard.writeText(shareUrl);
      setTimeout(() => setCopying(false), 2000);
    } catch {
      setCopying(false);
    }
  }, [shareUrl]);

  const isOwner = shareInfo?.is_owner ?? false;
  const isShared = shareInfo?.is_shared ?? false;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>チャットを共有</DialogTitle>
          <DialogDescription>
            共有を有効にすると、URLを知っている人がこのチャットを閲覧できます。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {isOwner ? (
            <>
              <div className="flex items-center justify-between">
                <Label htmlFor="share-toggle" className="text-sm font-medium">
                  共有を有効にする
                </Label>
                <Switch
                  id="share-toggle"
                  checked={isShared}
                  onCheckedChange={handleToggle}
                  disabled={toggling || isLoading}
                />
              </div>

              {isShared && shareUrl ? (
                <div className="space-y-2">
                  <Label className="text-sm text-muted-foreground">
                    共有URL
                  </Label>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 rounded-md border bg-muted px-3 py-2 text-sm truncate">
                      {shareUrl}
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={handleCopy}
                      disabled={copying}
                    >
                      {copying ? (
                        <Check className="h-4 w-4 text-green-600" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      asChild
                    >
                      <a href={shareUrl} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    </Button>
                  </div>
                </div>
              ) : null}
            </>
          ) : (
            <div className="text-sm text-muted-foreground">
              {isShared
                ? "このチャットはオーナーによって共有されています。閲覧のみ可能です。"
                : "このチャットへのアクセス権がありません。"}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
