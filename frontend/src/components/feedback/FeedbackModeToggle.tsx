"use client";

import { MessageSquareText } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface FeedbackModeToggleProps {
  isActive: boolean;
  onToggle: (active: boolean) => void;
}

export function FeedbackModeToggle({ isActive, onToggle }: FeedbackModeToggleProps) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={isActive ? "default" : "ghost"}
            size="sm"
            className={`h-8 gap-1.5 text-xs ${
              isActive
                ? "bg-amber-500 hover:bg-amber-600 text-white"
                : "text-muted-foreground"
            }`}
            onClick={() => onToggle(!isActive)}
          >
            <MessageSquareText className="w-3.5 h-3.5" />
            {isActive ? <><span className="hidden sm:inline">FBモード ON</span><span className="sm:hidden">FB</span></> : "FB"}
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>{isActive ? "フィードバックモードを終了" : "フィードバックモード: テキスト選択でアノテーション追加"}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
