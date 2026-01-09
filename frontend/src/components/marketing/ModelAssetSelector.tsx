"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  Check,
  ChevronsUpDown,
  Settings2,
  Sparkles,
  Plus,
  Globe,
  Code2,
  BarChart3,
  Search,
  ExternalLink,
  FileText,
  LayoutTemplate,
  Megaphone,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

export type ModelAsset = {
  id: string;
  name: string;
  description?: string;
  reasoning_effort?: "low" | "medium" | "high";
  verbosity?: "low" | "medium" | "high";
  enable_web_search?: boolean;
  enable_code_interpreter?: boolean;
  enable_ga4?: boolean;
  enable_meta_ads?: boolean;
  enable_gsc?: boolean;
  enable_ahrefs?: boolean;
  enable_wordpress?: boolean;
  enable_canvas?: boolean;
  system_prompt_addition?: string | null;
  visibility?: "public" | "private";
  created_by?: string | null;
  created_by_email?: string | null;
  created_by_name?: string | null;
};

type Props = {
  assets: ModelAsset[];
  selectedId: string;
  onSelect: (id: string) => void;
  onManageClick: () => void;
  onCreateClick: () => void;
};

const TOOL_ICONS: Record<string, React.ReactNode> = {
  enable_web_search: <Globe className="h-3 w-3" />,
  enable_code_interpreter: <Code2 className="h-3 w-3" />,
  enable_ga4: <BarChart3 className="h-3 w-3" />,
  enable_meta_ads: <Megaphone className="h-3 w-3" />,
  enable_gsc: <Search className="h-3 w-3" />,
  enable_ahrefs: <ExternalLink className="h-3 w-3" />,
  enable_wordpress: <FileText className="h-3 w-3" />,
  enable_canvas: <LayoutTemplate className="h-3 w-3" />,
};

const TOOL_LABELS: Record<string, string> = {
  enable_web_search: "Web",
  enable_code_interpreter: "Code",
  enable_ga4: "GA4",
  enable_meta_ads: "Meta",
  enable_gsc: "GSC",
  enable_ahrefs: "Ahrefs",
  enable_wordpress: "WP",
  enable_canvas: "Canvas",
};

export function ModelAssetSelector({
  assets,
  selectedId,
  onSelect,
  onManageClick,
  onCreateClick,
}: Props) {
  const [open, setOpen] = useState(false);

  const selectedAsset = assets.find((a) => a.id === selectedId);

  const getEnabledTools = (asset: ModelAsset) => {
    return Object.entries(asset)
      .filter(([key, value]) => key.startsWith("enable_") && value === true)
      .map(([key]) => key);
  };

  const enabledToolsCount = selectedAsset ? getEnabledTools(selectedAsset).length : 0;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-[280px] justify-between bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80"
        >
          <div className="flex items-center gap-2 truncate">
            {selectedAsset?.id === "standard" && (
              <Sparkles className="h-4 w-4 text-primary shrink-0" />
            )}
            <span className="truncate font-medium">
              {selectedAsset?.name || "モデルを選択"}
            </span>
            {enabledToolsCount > 0 && (
              <Badge variant="secondary" className="ml-auto shrink-0 text-xs">
                {enabledToolsCount}ツール
              </Badge>
            )}
          </div>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[400px] p-0" align="start">
        <Command>
          <CommandInput placeholder="モデルを検索..." className="h-9" />
          <CommandList className="max-h-[450px] overflow-y-auto">
            <CommandEmpty>モデルが見つかりません</CommandEmpty>
            <CommandGroup>
              <div className="max-h-[280px] overflow-y-auto">
                {assets.map((asset) => {
                  const enabledTools = getEnabledTools(asset);
                  const isStandard = asset.id === "standard";
                  const isSelected = asset.id === selectedId;

                  return (
                    <CommandItem
                      key={asset.id}
                      value={`${asset.name} ${asset.description || ""}`}
                      onSelect={() => {
                        onSelect(asset.id);
                        setOpen(false);
                      }}
                      className="flex flex-col items-start gap-2 p-3 aria-selected:bg-accent cursor-pointer"
                    >
                      <div className="flex items-center justify-between w-full gap-2">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <Check
                            className={cn(
                              "h-4 w-4 shrink-0",
                              isSelected ? "opacity-100" : "opacity-0"
                            )}
                          />
                          {isStandard && (
                            <Sparkles className="h-4 w-4 text-primary shrink-0" />
                          )}
                          <span className="font-medium truncate">{asset.name}</span>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <Badge variant="outline" className="text-xs font-mono px-1.5 py-0">
                            {asset.reasoning_effort || "high"}
                          </Badge>
                        </div>
                      </div>

                      {asset.description && (
                        <p className="text-xs text-muted-foreground line-clamp-2 ml-6">
                          {asset.description}
                        </p>
                      )}

                      <div className="flex items-center gap-2 ml-6 text-[11px] text-muted-foreground">
                        <Badge variant={asset.visibility === "private" ? "outline" : "secondary"} className="h-5 px-2">
                          {asset.visibility === "private" ? "Private" : "Public"}
                        </Badge>
                        {asset.created_by_email && (
                          <span className="truncate" title={asset.created_by_email}>
                            作成: {asset.created_by_name || asset.created_by_email}
                          </span>
                        )}
                      </div>

                      {enabledTools.length > 0 && (
                        <div className="flex flex-wrap gap-1 ml-6">
                          {enabledTools.slice(0, 6).map((tool) => (
                            <Badge
                              key={tool}
                              variant="secondary"
                              className="text-xs h-5 px-1.5 flex items-center gap-1"
                            >
                              {TOOL_ICONS[tool]}
                              <span className="text-[10px]">{TOOL_LABELS[tool]}</span>
                            </Badge>
                          ))}
                          {enabledTools.length > 6 && (
                            <Badge variant="secondary" className="text-xs h-5 px-1.5">
                              +{enabledTools.length - 6}
                            </Badge>
                          )}
                        </div>
                      )}
                    </CommandItem>
                  );
                })}
              </div>
            </CommandGroup>
            <CommandSeparator />
            <CommandGroup>
              <CommandItem
                onSelect={() => {
                  onCreateClick();
                  setOpen(false);
                }}
                className="cursor-pointer"
              >
                <Plus className="mr-2 h-4 w-4" />
                <span className="font-medium">新規モデルを作成</span>
              </CommandItem>
              <CommandItem
                onSelect={() => {
                  onManageClick();
                  setOpen(false);
                }}
                className="cursor-pointer"
              >
                <Settings2 className="mr-2 h-4 w-4" />
                <span className="font-medium">モデル管理画面を開く</span>
              </CommandItem>
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
