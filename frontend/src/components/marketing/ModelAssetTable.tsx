"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Edit,
  Trash2,
  Plus,
  Search,
  Sparkles,
  Globe,
  Code2,
  BarChart3,
  Search as SearchIcon,
  ExternalLink,
  FileText,
} from "lucide-react";
import { ModelAssetForm } from "./ModelAssetForm";

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
  assets: ModelAsset[];
  onSave: (asset: Partial<ModelAsset>, assetId?: string) => Promise<void>;
  onDelete: (assetId: string) => Promise<void>;
};

const TOOL_ICONS: Record<string, { icon: React.ReactNode; label: string }> = {
  enable_web_search: { icon: <Globe className="h-3.5 w-3.5" />, label: "Web" },
  enable_code_interpreter: { icon: <Code2 className="h-3.5 w-3.5" />, label: "Code" },
  enable_ga4: { icon: <BarChart3 className="h-3.5 w-3.5" />, label: "GA4" },
  enable_gsc: { icon: <SearchIcon className="h-3.5 w-3.5" />, label: "GSC" },
  enable_ahrefs: { icon: <ExternalLink className="h-3.5 w-3.5" />, label: "Ahrefs" },
  enable_wordpress: { icon: <FileText className="h-3.5 w-3.5" />, label: "WP" },
};

export function ModelAssetTable({ assets, onSave, onDelete }: Props) {
  const [searchQuery, setSearchQuery] = useState("");
  const [editingAsset, setEditingAsset] = useState<ModelAsset | null>(null);
  const [deletingAssetId, setDeletingAssetId] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const filteredAssets = assets.filter((asset) => {
    const query = searchQuery.toLowerCase();
    return (
      asset.name.toLowerCase().includes(query) ||
      asset.description?.toLowerCase().includes(query) ||
      asset.id.toLowerCase().includes(query)
    );
  });

  const getEnabledTools = (asset: ModelAsset) => {
    return Object.entries(asset)
      .filter(([key, value]) => key.startsWith("enable_") && value === true)
      .map(([key]) => key);
  };

  const handleEdit = (asset: ModelAsset) => {
    setEditingAsset(asset);
  };

  const handleDelete = async (assetId: string) => {
    if (assetId === "standard") {
      alert("スタンダードモデルは削除できません");
      return;
    }
    setActionLoading(true);
    try {
      await onDelete(assetId);
      setDeletingAssetId(null);
    } catch (error) {
      console.error(error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveEdit = async (form: Partial<ModelAsset>) => {
    if (!editingAsset) return;
    setActionLoading(true);
    try {
      await onSave(form, editingAsset.id);
      setEditingAsset(null);
    } catch (error) {
      console.error(error);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreate = async (form: Partial<ModelAsset>) => {
    setActionLoading(true);
    try {
      await onSave(form);
      setShowCreateDialog(false);
    } catch (error) {
      console.error(error);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* ヘッダー */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="名前、説明、IDで検索..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button onClick={() => setShowCreateDialog(true)} size="default">
          <Plus className="h-4 w-4 mr-2" />
          新規作成
        </Button>
      </div>

      {/* テーブル */}
      <div className="rounded-md border">
        <ScrollArea className="h-[500px]">
          <Table>
            <TableHeader className="sticky top-0 bg-muted/50 backdrop-blur">
              <TableRow>
                <TableHead className="w-[250px]">モデル名</TableHead>
                <TableHead className="w-[150px]">設定</TableHead>
                <TableHead>有効なツール</TableHead>
                <TableHead className="text-right w-[100px]">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAssets.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center">
                    <div className="flex flex-col items-center gap-2 text-muted-foreground">
                      <Search className="h-8 w-8 opacity-40" />
                      <p className="text-sm">
                        {searchQuery
                          ? "検索結果が見つかりませんでした"
                          : "モデルアセットがありません"}
                      </p>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                filteredAssets.map((asset) => {
                  const enabledTools = getEnabledTools(asset);
                  const isStandard = asset.id === "standard";

                  return (
                    <TableRow key={asset.id} className="group">
                      <TableCell>
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            {isStandard && (
                              <Sparkles className="h-4 w-4 text-primary shrink-0" />
                            )}
                            <span className="font-medium">{asset.name}</span>
                          </div>
                          {asset.description && (
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {asset.description}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-col gap-1.5">
                          <Badge variant="outline" className="w-fit text-xs font-mono">
                            推論: {asset.reasoning_effort || "high"}
                          </Badge>
                          <Badge variant="outline" className="w-fit text-xs font-mono">
                            詳細: {asset.verbosity || "medium"}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {enabledTools.length > 0 ? (
                            enabledTools.slice(0, 4).map((tool) => {
                              const config = TOOL_ICONS[tool];
                              return (
                                <Badge
                                  key={tool}
                                  variant="secondary"
                                  className="text-xs h-6 px-2 flex items-center gap-1"
                                >
                                  {config.icon}
                                  <span>{config.label}</span>
                                </Badge>
                              );
                            })
                          ) : (
                            <span className="text-xs text-muted-foreground">なし</span>
                          )}
                          {enabledTools.length > 4 && (
                            <Badge variant="secondary" className="text-xs h-6 px-2">
                              +{enabledTools.length - 4}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEdit(asset)}
                            className="h-8 w-8 p-0"
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          {!isStandard && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setDeletingAssetId(asset.id)}
                              className="h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </ScrollArea>
      </div>

      <div className="text-xs text-muted-foreground">
        {filteredAssets.length} 件のモデルアセット
        {searchQuery && ` (${assets.length}件中)`}
      </div>

      {/* 編集ダイアログ */}
      <Dialog open={!!editingAsset} onOpenChange={(open) => !open && setEditingAsset(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>モデルアセットを編集</DialogTitle>
          </DialogHeader>
          {editingAsset && (
            <ModelAssetForm
              initialValues={editingAsset}
              onSubmit={handleSaveEdit}
              loading={actionLoading}
              submitLabel="変更を保存"
            />
          )}
        </DialogContent>
      </Dialog>

      {/* 新規作成ダイアログ */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>モデルアセットを作成</DialogTitle>
          </DialogHeader>
          <ModelAssetForm
            onSubmit={handleCreate}
            loading={actionLoading}
            submitLabel="作成"
          />
        </DialogContent>
      </Dialog>

      {/* 削除確認ダイアログ */}
      <AlertDialog
        open={!!deletingAssetId}
        onOpenChange={(open) => !open && setDeletingAssetId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>モデルアセットを削除しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              この操作は取り消せません。削除されたモデルアセットは復元できません。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={actionLoading}>キャンセル</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deletingAssetId && handleDelete(deletingAssetId)}
              disabled={actionLoading}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {actionLoading ? "削除中..." : "削除"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
