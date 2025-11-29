"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Globe, Code2, BarChart3, Search, ExternalLink, FileText } from "lucide-react";

export type ModelAsset = {
  id: string;
  name: string;
  description?: string;
  reasoning_effort?: "low" | "medium" | "high";
  verbosity?: "low" | "medium" | "high";
  enable_web_search?: boolean;
  enable_code_interpreter?: boolean;
  enable_ga4?: boolean;
  enable_gsc?: boolean;
  enable_ahrefs?: boolean;
  enable_wordpress?: boolean;
  system_prompt_addition?: string | null;
};

type Props = {
  initialValues?: Partial<ModelAsset>;
  onSubmit: (form: Partial<ModelAsset>) => void;
  loading: boolean;
  submitLabel?: string;
};

const TOOL_CONFIG = [
  {
    key: "enable_web_search",
    label: "Web検索",
    description: "Google検索でリアルタイム情報を取得",
    icon: <Globe className="h-4 w-4" />,
  },
  {
    key: "enable_code_interpreter",
    label: "コード実行",
    description: "Pythonコードの実行とデータ分析",
    icon: <Code2 className="h-4 w-4" />,
  },
  {
    key: "enable_ga4",
    label: "Google Analytics 4",
    description: "GA4データの取得と分析",
    icon: <BarChart3 className="h-4 w-4" />,
  },
  {
    key: "enable_gsc",
    label: "Google Search Console",
    description: "検索パフォーマンスデータの取得",
    icon: <Search className="h-4 w-4" />,
  },
  {
    key: "enable_ahrefs",
    label: "Ahrefs",
    description: "被リンクとSEOデータの分析",
    icon: <ExternalLink className="h-4 w-4" />,
  },
  {
    key: "enable_wordpress",
    label: "WordPress",
    description: "WordPress記事の管理",
    icon: <FileText className="h-4 w-4" />,
  },
] as const;

export function ModelAssetForm({
  initialValues,
  onSubmit,
  loading,
  submitLabel = "保存",
}: Props) {
  const [name, setName] = useState(initialValues?.name || "");
  const [description, setDescription] = useState(initialValues?.description || "");
  const [reasoning, setReasoning] = useState<ModelAsset["reasoning_effort"]>(
    initialValues?.reasoning_effort || "high"
  );
  const [verbosity, setVerbosity] = useState<ModelAsset["verbosity"]>(
    initialValues?.verbosity || "medium"
  );
  const [systemPrompt, setSystemPrompt] = useState(
    initialValues?.system_prompt_addition || ""
  );
  const [toolFlags, setToolFlags] = useState({
    enable_web_search: initialValues?.enable_web_search ?? true,
    enable_code_interpreter: initialValues?.enable_code_interpreter ?? true,
    enable_ga4: initialValues?.enable_ga4 ?? true,
    enable_gsc: initialValues?.enable_gsc ?? true,
    enable_ahrefs: initialValues?.enable_ahrefs ?? true,
    enable_wordpress: initialValues?.enable_wordpress ?? true,
  });

  const toggleFlag = (key: keyof typeof toolFlags) => {
    setToolFlags((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      name,
      description,
      reasoning_effort: reasoning,
      verbosity,
      system_prompt_addition: systemPrompt || null,
      ...toolFlags,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* 基本情報 */}
      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="name" className="text-sm font-semibold">
            プリセット名 <span className="text-destructive">*</span>
          </Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例: 女性転職分析プリセット"
            required
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="description" className="text-sm font-semibold">
            説明（任意）
          </Label>
          <Input
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="このプリセットの用途や特徴"
          />
        </div>
      </div>

      <Separator />

      {/* モデル設定 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">モデル設定</CardTitle>
          <CardDescription className="text-xs">
            AIの思考の深さと出力の詳細度を調整
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="reasoning" className="text-sm">
              推論レベル (Reasoning Effort)
            </Label>
            <Select value={reasoning} onValueChange={(v) => setReasoning(v as any)}>
              <SelectTrigger id="reasoning">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Low - 高速</SelectItem>
                <SelectItem value="medium">Medium - バランス</SelectItem>
                <SelectItem value="high">High - 深い思考</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="verbosity" className="text-sm">
              詳細度 (Verbosity)
            </Label>
            <Select value={verbosity} onValueChange={(v) => setVerbosity(v as any)}>
              <SelectTrigger id="verbosity">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Low - 簡潔</SelectItem>
                <SelectItem value="medium">Medium - 標準</SelectItem>
                <SelectItem value="high">High - 詳細</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* ツール設定 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">ツール / MCP設定</CardTitle>
          <CardDescription className="text-xs">
            有効にするツールを選択してください
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {TOOL_CONFIG.map(({ key, label, description, icon }) => (
            <div
              key={key}
              className="flex items-center justify-between space-x-4 rounded-lg border p-4 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-start space-x-3 flex-1">
                <div className="mt-1 text-muted-foreground">{icon}</div>
                <div className="space-y-0.5 flex-1">
                  <Label
                    htmlFor={key}
                    className="text-sm font-medium cursor-pointer leading-none"
                  >
                    {label}
                  </Label>
                  <p className="text-xs text-muted-foreground">{description}</p>
                </div>
              </div>
              <Switch
                id={key}
                checked={toolFlags[key as keyof typeof toolFlags]}
                onCheckedChange={() => toggleFlag(key as keyof typeof toolFlags)}
              />
            </div>
          ))}
        </CardContent>
      </Card>

      {/* カスタムプロンプト */}
      <div className="space-y-2">
        <Label htmlFor="system-prompt" className="text-sm font-semibold">
          追加システムプロンプト（任意）
        </Label>
        <p className="text-xs text-muted-foreground mb-2">
          MARKETING_INSTRUCTIONSの前に挿入される追加指示
        </p>
        <Textarea
          id="system-prompt"
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
          rows={6}
          placeholder="例: 女性向けの記事ではインクルーシブな表現を優先し、統計は最新の厚労省資料を参照すること。"
          className="font-mono text-xs resize-none"
        />
      </div>

      <Separator />

      <div className="flex justify-end gap-3">
        <Button type="submit" disabled={loading || !name.trim()} size="lg">
          {loading ? "保存中..." : submitLabel}
        </Button>
      </div>
    </form>
  );
}
