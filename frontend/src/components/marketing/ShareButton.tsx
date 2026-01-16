"use client";

import * as React from "react";
import { Share2, Copy, Check, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

export type ShareInfo = {
  thread_id: string;
  is_shared: boolean;
  shared_at: string | null;
  shared_by_email: string | null;
  is_owner: boolean;
  can_toggle: boolean;
  share_url: string | null;
};

type ShareButtonProps = {
  threadId: string;
  shareInfo: ShareInfo | null;
  onToggle: (isShared: boolean) => Promise<void>;
  disabled?: boolean;
  isLoading?: boolean;
};

export function ShareButton({
  threadId,
  shareInfo,
  onToggle,
  disabled = false,
  isLoading: externalLoading = false,
}: ShareButtonProps) {
  const [isToggling, setIsToggling] = React.useState(false);
  const [copied, setCopied] = React.useState(false);
  const [open, setOpen] = React.useState(false);

  // Hide only if we know for sure user is NOT the owner (shareInfo loaded and is_owner=false)
  // Show button while loading (shareInfo=null) or if user is owner
  if (shareInfo !== null && !shareInfo.is_owner) {
    return null;
  }

  const isLoading = externalLoading || shareInfo === null;

  const handleToggle = async (checked: boolean) => {
    setIsToggling(true);
    try {
      await onToggle(checked);
    } finally {
      setIsToggling(false);
    }
  };

  const handleCopy = async () => {
    const url = `${window.location.origin}/marketing/${threadId}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy URL", err);
    }
  };

  const shareUrl = `${typeof window !== "undefined" ? window.location.origin : ""}/marketing/${threadId}`;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          disabled={disabled}
          className="gap-1.5 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80"
        >
          <Share2 className="h-4 w-4" />
          <span className="hidden sm:inline">共有</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>会話を共有</DialogTitle>
          <DialogDescription>
            共有を有効にすると、このアプリにログインしているユーザーがこの会話を閲覧できるようになります。
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-2 text-sm text-muted-foreground">読み込み中...</span>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <Label htmlFor="share-toggle" className="text-sm font-medium">
                  リンクで共有を有効にする
                </Label>
                <div className="flex items-center gap-2">
                  {isToggling && <Loader2 className="h-4 w-4 animate-spin" />}
                  <Switch
                    id="share-toggle"
                    checked={shareInfo?.is_shared ?? false}
                    onCheckedChange={handleToggle}
                    disabled={isToggling || !shareInfo?.can_toggle}
                  />
                </div>
              </div>

              {shareInfo?.is_shared && (
                <div className="space-y-2">
                  <Label className="text-sm text-muted-foreground">共有URL</Label>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={shareUrl}
                      className="flex-1 rounded-md border bg-muted px-3 py-2 text-sm"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleCopy}
                      className="shrink-0"
                    >
                      {copied ? (
                        <Check className="h-4 w-4 text-green-500" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    共有された会話は閲覧専用です。メッセージの送信はできません。
                  </p>
                </div>
              )}

              {shareInfo?.shared_at && shareInfo?.shared_by_email && (
                <p className="text-xs text-muted-foreground">
                  {shareInfo.shared_by_email} が{" "}
                  {new Date(shareInfo.shared_at).toLocaleDateString("ja-JP")} に共有
                </p>
              )}
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
