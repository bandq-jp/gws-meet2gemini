"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useUser } from "@clerk/nextjs";
import { useImageGen } from "@/hooks/use-image-gen";
import type { ImageGenTemplate, ImageGenMessage, ImageGenReference } from "@/lib/api";
import { getRefImageUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Plus,
  Send,
  ImageIcon,
  Layers,
  Sparkles,
  Download,
  X,
  Upload,
  Trash2,
  Settings2,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Loader2,
  GalleryHorizontalEnd,
  Pencil,
  LayoutGrid,
  Maximize2,
  ChevronDown,
  FolderOpen,
} from "lucide-react";
import toast from "react-hot-toast";

// ── Constants ──

const ASPECT_RATIOS = [
  { value: "auto", label: "自動" },
  { value: "1:1", label: "1:1" },
  { value: "2:3", label: "2:3" },
  { value: "3:2", label: "3:2" },
  { value: "3:4", label: "3:4" },
  { value: "4:3", label: "4:3" },
  { value: "4:5", label: "4:5" },
  { value: "5:4", label: "5:4" },
  { value: "9:16", label: "9:16" },
  { value: "16:9", label: "16:9" },
  { value: "21:9", label: "21:9" },
];

const RESOLUTIONS = [
  { value: "1K", label: "1K", desc: "1024px" },
  { value: "2K", label: "2K", desc: "2048px" },
  { value: "4K", label: "4K", desc: "4096px" },
];

const CATEGORIES = [
  { value: "blog_eyecatch", label: "ブログアイキャッチ" },
  { value: "ad_banner", label: "広告バナー" },
  { value: "social", label: "SNS投稿" },
  { value: "product", label: "商品画像" },
  { value: "custom", label: "カスタム" },
];

// ── Template Dialog ──

function TemplateDialog({
  open,
  onOpenChange,
  template,
  onSave,
  onUploadRef,
  onDeleteRef,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  template: ImageGenTemplate | null;
  onSave: (data: Partial<ImageGenTemplate>) => Promise<void>;
  onUploadRef: (templateId: string, file: File, label: string) => Promise<ImageGenReference>;
  onDeleteRef: (refId: string, templateId: string) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("custom");
  const [aspectRatio, setAspectRatio] = useState("auto");
  const [imageSize, setImageSize] = useState("1K");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploadingRef, setUploadingRef] = useState(false);
  const [refLabel, setRefLabel] = useState("style");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (template) {
      setName(template.name || "");
      setDescription(template.description || "");
      setCategory(template.category || "custom");
      setAspectRatio(template.aspect_ratio || "auto");
      setImageSize(template.image_size || "1K");
      setSystemPrompt(template.system_prompt || "");
    } else {
      setName("");
      setDescription("");
      setCategory("custom");
      setAspectRatio("auto");
      setImageSize("1K");
      setSystemPrompt("");
    }
  }, [template, open]);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await onSave({
        name: name.trim(),
        description: description.trim() || undefined,
        category,
        aspect_ratio: aspectRatio,
        image_size: imageSize,
        system_prompt: systemPrompt.trim() || undefined,
      });
      onOpenChange(false);
    } catch {
      toast.error("保存に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length || !template?.id) return;
    setUploadingRef(true);
    try {
      for (const file of Array.from(files)) {
        await onUploadRef(template.id, file, refLabel);
      }
      toast.success("リファレンス画像を追加しました");
    } catch {
      toast.error("アップロードに失敗しました");
    } finally {
      setUploadingRef(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    if (!template?.id) return;
    const files = Array.from(e.dataTransfer.files).filter((f) =>
      f.type.startsWith("image/")
    );
    if (!files.length) return;
    setUploadingRef(true);
    try {
      for (const file of files) {
        await onUploadRef(template.id, file, refLabel);
      }
      toast.success("リファレンス画像を追加しました");
    } catch {
      toast.error("アップロードに失敗しました");
    } finally {
      setUploadingRef(false);
    }
  };

  const refs = template?.image_gen_references || [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold tracking-tight">
            {template ? "テンプレートを編集" : "新規テンプレート"}
          </DialogTitle>
          <DialogDescription>
            リファレンス画像を設定し、画像生成のスタイルを定義します
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 pt-2">
          {/* Name & Category */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                テンプレート名
              </Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例: WPアイキャッチ"
                className="h-9"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                カテゴリ
              </Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c.value} value={c.value}>
                      {c.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              説明
            </Label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="このテンプレートの用途や特徴"
              className="h-9"
            />
          </div>

          {/* Aspect Ratio & Resolution */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                アスペクト比
              </Label>
              <Select value={aspectRatio} onValueChange={setAspectRatio}>
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ASPECT_RATIOS.map((r) => (
                    <SelectItem key={r.value} value={r.value}>
                      {r.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                解像度
              </Label>
              <Select value={imageSize} onValueChange={setImageSize}>
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {RESOLUTIONS.map((r) => (
                    <SelectItem key={r.value} value={r.value}>
                      {r.label} ({r.desc})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* System Prompt */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              システムプロンプト
            </Label>
            <Textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="画像生成時に常に適用されるスタイル指示 (例: ブランドカラーを使用し、クリーンでモダンなデザインで...)"
              className="min-h-[80px] text-sm resize-none"
            />
          </div>

          {/* Reference Images (only for existing templates) */}
          {template && (
            <>
              <Separator />
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      リファレンス画像
                    </Label>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      最大14枚 (人物最大5枚) ・ 現在 {refs.length}/14
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Select value={refLabel} onValueChange={setRefLabel}>
                      <SelectTrigger className="h-7 text-xs w-24">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="style">スタイル</SelectItem>
                        <SelectItem value="object">オブジェクト</SelectItem>
                        <SelectItem value="person">人物</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="h-7 text-xs"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploadingRef || refs.length >= 14}
                    >
                      {uploadingRef ? (
                        <Loader2 className="h-3 w-3 animate-spin mr-1" />
                      ) : (
                        <Upload className="h-3 w-3 mr-1" />
                      )}
                      追加
                    </Button>
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      accept="image/*"
                      className="hidden"
                      onChange={handleFileSelect}
                    />
                  </div>
                </div>

                {/* Drop zone */}
                <div
                  onDrop={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                  className="border-2 border-dashed border-border/60 rounded-lg p-4 text-center transition-colors hover:border-primary/30 hover:bg-muted/30"
                >
                  {refs.length > 0 ? (
                    <div className="grid grid-cols-4 gap-2">
                      {refs.map((ref) => (
                        <div
                          key={ref.id}
                          className="relative group rounded-md overflow-hidden bg-muted aspect-square"
                        >
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={getRefImageUrl(ref.storage_path)}
                            alt={ref.filename}
                            className="absolute inset-0 w-full h-full object-cover"
                          />
                          <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <Button
                              size="sm"
                              variant="destructive"
                              className="h-5 w-5 p-0 rounded-full"
                              onClick={() =>
                                template?.id &&
                                onDeleteRef(ref.id, template.id)
                              }
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          </div>
                          <div className="absolute bottom-0 left-0 right-0 bg-black/50 px-1.5 py-0.5">
                            <span className="text-[10px] text-white truncate block">
                              {ref.filename}
                            </span>
                          </div>
                          <Badge
                            variant="secondary"
                            className="absolute top-1 left-1 text-[9px] h-4 px-1"
                          >
                            {ref.label === "person"
                              ? "人物"
                              : ref.label === "object"
                              ? "素材"
                              : "Style"}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="py-4">
                      <Upload className="h-8 w-8 mx-auto text-muted-foreground/40 mb-2" />
                      <p className="text-sm text-muted-foreground">
                        ここに画像をドロップ、またはクリックして選択
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        <div className="flex justify-end gap-2 pt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            キャンセル
          </Button>
          <Button onClick={handleSave} disabled={!name.trim() || saving}>
            {saving && <Loader2 className="h-4 w-4 animate-spin mr-1.5" />}
            {template ? "更新" : "作成"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ── Lightbox ──

function Lightbox({
  src,
  onClose,
}: {
  src: string;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center cursor-pointer"
      onClick={onClose}
    >
      <Button
        variant="ghost"
        size="sm"
        className="absolute top-4 right-4 text-white hover:bg-white/10"
        onClick={onClose}
      >
        <X className="h-5 w-5" />
      </Button>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt="Generated"
        className="max-w-[90vw] max-h-[90vh] object-contain rounded-lg shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  );
}

// ── Helpers ──

/** Convert backend image_url (/api/v1/...) to BFF proxy path (/api/proxy/...) */
function toProxyUrl(url: string | undefined | null): string {
  if (!url) return "";
  return url.replace(/^\/api\/v1\//, "/api/proxy/");
}

// ── Main Page ──

export default function ImageGenPage() {
  const { user } = useUser();
  const {
    templates,
    sessions,
    currentSession,
    messages,
    isLoading,
    isGenerating,
    error,
    fetchTemplates,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    uploadReference,
    deleteReference,
    fetchSessions,
    createSession,
    loadSession,
    setCurrentSession,
    generateImage,
    setError,
  } = useImageGen();

  const [prompt, setPrompt] = useState("");
  const [aspectRatio, setAspectRatio] = useState("auto");
  const [imageSize, setImageSize] = useState("1K");
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [showLeftPanel, setShowLeftPanel] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ImageGenTemplate | null>(null);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Initialize
  useEffect(() => {
    fetchTemplates();
    fetchSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Clear error on timeout
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error, setError]);

  const selectedTemplate = templates.find((t) => t.id === selectedTemplateId);

  const handleNewSession = useCallback(async () => {
    const email = user?.emailAddresses[0]?.emailAddress;
    await createSession({
      template_id: selectedTemplateId || undefined,
      title: selectedTemplate?.name
        ? `${selectedTemplate.name} - ${new Date().toLocaleDateString("ja-JP")}`
        : `セッション - ${new Date().toLocaleDateString("ja-JP")}`,
      aspect_ratio: aspectRatio,
      image_size: imageSize,
      created_by: user?.id,
      created_by_email: email,
    });
  }, [
    createSession,
    selectedTemplateId,
    selectedTemplate,
    aspectRatio,
    imageSize,
    user,
  ]);

  const handleGenerate = useCallback(async () => {
    if (!prompt.trim() || isGenerating) return;

    if (!currentSession) {
      await handleNewSession();
    }

    await generateImage(prompt.trim(), {
      aspect_ratio: aspectRatio !== "auto" ? aspectRatio : undefined,
      image_size: imageSize,
    });
    setPrompt("");
    textareaRef.current?.focus();
  }, [
    prompt,
    isGenerating,
    currentSession,
    handleNewSession,
    generateImage,
    aspectRatio,
    imageSize,
  ]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleGenerate();
    }
  };

  const handleSaveTemplate = async (data: Partial<ImageGenTemplate>) => {
    if (editingTemplate) {
      await updateTemplate(editingTemplate.id, data);
    } else {
      const email = user?.emailAddresses[0]?.emailAddress;
      const result = await createTemplate({
        ...data,
        name: data.name || "",
        created_by: user?.id,
        created_by_email: email,
      });
      setEditingTemplate(result);
    }
  };

  const generatedImages = messages.filter(
    (m) => m.role === "assistant" && m.image_url
  );

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex flex-col h-[calc(100vh-2rem)] font-[family-name:var(--font-geist-sans)]">
        {/* ── Header ── */}
        <header className="shrink-0 flex items-center gap-3 px-5 py-3 border-b border-border/60 bg-background/80 backdrop-blur-sm">
          <div className="flex items-center gap-2.5 mr-auto">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--brand-300)] to-[var(--brand-400)] text-white">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-sm font-semibold tracking-tight leading-none">
                画像生成スタジオ
              </h1>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                Gemini 3 Pro Image Preview
              </p>
            </div>
          </div>

          {/* Template Selector */}
          <Select
            value={selectedTemplateId || "none"}
            onValueChange={(v) =>
              setSelectedTemplateId(v === "none" ? null : v)
            }
          >
            <SelectTrigger className="h-8 w-44 text-xs">
              <Layers className="h-3.5 w-3.5 mr-1.5 shrink-0 text-muted-foreground" />
              <SelectValue placeholder="テンプレート" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">テンプレートなし</SelectItem>
              {templates.map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Aspect Ratio */}
          <Select value={aspectRatio} onValueChange={setAspectRatio}>
            <SelectTrigger className="h-8 w-24 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ASPECT_RATIOS.map((r) => (
                <SelectItem key={r.value} value={r.value}>
                  {r.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Resolution */}
          <div className="flex items-center border rounded-md h-8 overflow-hidden">
            {RESOLUTIONS.map((r) => (
              <button
                key={r.value}
                onClick={() => setImageSize(r.value)}
                className={`px-2.5 h-full text-xs font-medium transition-colors ${
                  imageSize === r.value
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>

          {/* New Session */}
          <Button
            size="sm"
            className="h-8 text-xs gap-1.5"
            onClick={handleNewSession}
          >
            <Plus className="h-3.5 w-3.5" />
            新規セッション
          </Button>

          {/* Panel toggles */}
          <Separator orientation="vertical" className="h-5 mx-1" />
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setShowLeftPanel((v) => !v)}
              >
                {showLeftPanel ? (
                  <PanelLeftClose className="h-4 w-4" />
                ) : (
                  <PanelLeftOpen className="h-4 w-4" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">テンプレート</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={() => setShowRightPanel((v) => !v)}
              >
                {showRightPanel ? (
                  <PanelRightClose className="h-4 w-4" />
                ) : (
                  <PanelRightOpen className="h-4 w-4" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">ギャラリー</TooltipContent>
          </Tooltip>
        </header>

        {/* ── Error Banner ── */}
        {error && (
          <div className="shrink-0 px-5 py-2 bg-destructive/10 text-destructive text-xs flex items-center gap-2">
            <span className="flex-1">{error}</span>
            <Button
              variant="ghost"
              size="sm"
              className="h-5 w-5 p-0"
              onClick={() => setError(null)}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        )}

        {/* ── Main 3-Column Layout ── */}
        <div className="flex-1 flex overflow-hidden">
          {/* LEFT: Templates */}
          {showLeftPanel && (
            <aside className="w-64 shrink-0 border-r border-border/60 flex flex-col bg-muted/20">
              <div className="flex items-center justify-between px-3 py-2.5 border-b border-border/40">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  テンプレート
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0"
                  onClick={() => {
                    setEditingTemplate(null);
                    setTemplateDialogOpen(true);
                  }}
                >
                  <Plus className="h-3.5 w-3.5" />
                </Button>
              </div>
              <ScrollArea className="flex-1">
                <div className="p-2 space-y-1">
                  {templates.length === 0 && !isLoading && (
                    <div className="py-8 text-center">
                      <FolderOpen className="h-8 w-8 mx-auto text-muted-foreground/30 mb-2" />
                      <p className="text-xs text-muted-foreground">
                        テンプレートがありません
                      </p>
                      <Button
                        variant="link"
                        size="sm"
                        className="text-xs mt-1 h-auto p-0"
                        onClick={() => {
                          setEditingTemplate(null);
                          setTemplateDialogOpen(true);
                        }}
                      >
                        作成する
                      </Button>
                    </div>
                  )}
                  {templates.map((t) => {
                    const refCount = t.image_gen_references?.length || 0;
                    const isSelected = selectedTemplateId === t.id;
                    return (
                      <div
                        key={t.id}
                        role="button"
                        tabIndex={0}
                        onClick={() => setSelectedTemplateId(isSelected ? null : t.id)}
                        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setSelectedTemplateId(isSelected ? null : t.id); }}
                        className={`w-full text-left rounded-lg p-2.5 transition-all group cursor-pointer ${
                          isSelected
                            ? "bg-primary/8 ring-1 ring-primary/20"
                            : "hover:bg-muted/60"
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <div className="w-10 h-10 shrink-0 rounded-md bg-gradient-to-br from-muted to-muted/60 flex items-center justify-center">
                            <ImageIcon className="h-4 w-4 text-muted-foreground/60" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate leading-tight">
                              {t.name}
                            </p>
                            <div className="flex items-center gap-1.5 mt-1">
                              <Badge
                                variant="secondary"
                                className="text-[10px] h-4 px-1"
                              >
                                {t.aspect_ratio || "auto"}
                              </Badge>
                              <Badge
                                variant="secondary"
                                className="text-[10px] h-4 px-1"
                              >
                                {t.image_size || "1K"}
                              </Badge>
                              {refCount > 0 && (
                                <Badge
                                  variant="outline"
                                  className="text-[10px] h-4 px-1"
                                >
                                  {refCount}枚
                                </Badge>
                              )}
                            </div>
                          </div>
                          <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-0.5">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0"
                              onClick={(e) => {
                                e.stopPropagation();
                                setEditingTemplate(t);
                                setTemplateDialogOpen(true);
                              }}
                            >
                              <Pencil className="h-3 w-3" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 text-destructive"
                              onClick={(e) => {
                                e.stopPropagation();
                                if (confirm("削除しますか？")) deleteTemplate(t.id);
                              }}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                        {t.description && (
                          <p className="text-[11px] text-muted-foreground mt-1.5 line-clamp-2 pl-12">
                            {t.description}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </ScrollArea>

              {/* Session History */}
              <div className="border-t border-border/40">
                <div className="flex items-center justify-between px-3 py-2">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    履歴
                  </span>
                </div>
                <ScrollArea className="max-h-40">
                  <div className="px-2 pb-2 space-y-0.5">
                    {sessions.slice(0, 10).map((s) => (
                      <button
                        key={s.id}
                        onClick={() => loadSession(s.id)}
                        className={`w-full text-left rounded-md px-2.5 py-1.5 text-xs transition-colors ${
                          currentSession?.id === s.id
                            ? "bg-primary/8 text-foreground"
                            : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                        }`}
                      >
                        <p className="truncate font-medium">
                          {s.title || "無題のセッション"}
                        </p>
                        <p className="text-[10px] opacity-60 mt-0.5">
                          {s.created_at
                            ? new Date(s.created_at).toLocaleDateString("ja-JP")
                            : ""}
                        </p>
                      </button>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            </aside>
          )}

          {/* CENTER: Chat/Generation Area */}
          <main className="flex-1 flex flex-col min-w-0">
            {/* Messages */}
            <ScrollArea className="flex-1">
              <div className="max-w-2xl mx-auto px-5 py-6 space-y-4">
                {messages.length === 0 && !isGenerating && (
                  <div className="flex flex-col items-center justify-center py-20 text-center">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--brand-100)]/40 to-[var(--brand-200)]/30 flex items-center justify-center mb-4">
                      <Sparkles className="h-7 w-7 text-[var(--brand-400)]" />
                    </div>
                    <h2 className="text-lg font-semibold tracking-tight mb-1">
                      画像を生成しましょう
                    </h2>
                    <p className="text-sm text-muted-foreground max-w-sm">
                      {selectedTemplate
                        ? `「${selectedTemplate.name}」テンプレートのスタイルで画像を生成します。プロンプトを入力してください。`
                        : "テンプレートを選択するか、直接プロンプトを入力して画像を生成できます。"}
                    </p>
                    {selectedTemplate &&
                      (selectedTemplate.image_gen_references?.length || 0) > 0 && (
                        <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
                          <Layers className="h-3.5 w-3.5" />
                          <span>
                            {selectedTemplate.image_gen_references?.length}
                            枚のリファレンス画像が適用されます
                          </span>
                        </div>
                      )}
                  </div>
                )}

                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${
                      msg.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-[85%] ${
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground rounded-2xl rounded-br-md px-4 py-2.5"
                          : "space-y-2"
                      }`}
                    >
                      {msg.text_content && (
                        <p
                          className={`text-sm leading-relaxed ${
                            msg.role === "assistant"
                              ? "text-foreground bg-muted/50 rounded-2xl rounded-bl-md px-4 py-2.5"
                              : ""
                          }`}
                        >
                          {msg.text_content}
                        </p>
                      )}
                      {toProxyUrl(msg.image_url) && (
                        <div className="relative group rounded-xl overflow-hidden border border-border/40 shadow-sm max-w-md">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={toProxyUrl(msg.image_url)}
                            alt="Generated image"
                            className="w-full h-auto cursor-pointer transition-transform hover:scale-[1.02]"
                            onClick={() =>
                              toProxyUrl(msg.image_url) && setLightboxSrc(toProxyUrl(msg.image_url))
                            }
                          />
                          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                            <Button
                              variant="secondary"
                              size="sm"
                              className="h-7 w-7 p-0 bg-white/90 hover:bg-white shadow-sm"
                              onClick={() =>
                                toProxyUrl(msg.image_url) && setLightboxSrc(toProxyUrl(msg.image_url))
                              }
                            >
                              <Maximize2 className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              className="h-7 w-7 p-0 bg-white/90 hover:bg-white shadow-sm"
                              asChild
                            >
                              <a
                                href={toProxyUrl(msg.image_url)}
                                download
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                <Download className="h-3.5 w-3.5" />
                              </a>
                            </Button>
                          </div>
                          {msg.metadata && (
                            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/40 to-transparent p-2 pt-6 opacity-0 group-hover:opacity-100 transition-opacity">
                              <div className="flex items-center gap-2 text-[10px] text-white/80">
                                {String((msg.metadata as Record<string, unknown>)
                                  ?.aspect_ratio || '') && (
                                  <span>
                                    {String(
                                      (msg.metadata as Record<string, unknown>)
                                        ?.aspect_ratio ?? ''
                                    )}
                                  </span>
                                )}
                                {String((msg.metadata as Record<string, unknown>)
                                  ?.image_size || '') && (
                                  <span>
                                    {String(
                                      (msg.metadata as Record<string, unknown>)
                                        ?.image_size ?? ''
                                    )}
                                  </span>
                                )}
                                {!!(msg.metadata as Record<string, unknown>)
                                  ?.latency_ms && (
                                  <span>
                                    {Number(
                                      (msg.metadata as Record<string, unknown>)
                                        ?.latency_ms ?? 0
                                    ) / 1000}
                                    s
                                  </span>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {/* Generating indicator */}
                {isGenerating && (
                  <div className="flex justify-start">
                    <div className="bg-muted/50 rounded-2xl rounded-bl-md px-5 py-3 flex items-center gap-3">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 rounded-full bg-[var(--brand-300)] animate-bounce [animation-delay:0ms]" />
                        <span className="w-2 h-2 rounded-full bg-[var(--brand-300)] animate-bounce [animation-delay:150ms]" />
                        <span className="w-2 h-2 rounded-full bg-[var(--brand-300)] animate-bounce [animation-delay:300ms]" />
                      </div>
                      <span className="text-xs text-muted-foreground">
                        画像を生成中...
                      </span>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* Prompt Input */}
            <div className="shrink-0 border-t border-border/60 bg-background/80 backdrop-blur-sm px-5 py-3">
              <div className="max-w-2xl mx-auto">
                <div className="relative">
                  <Textarea
                    ref={textareaRef}
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={
                      selectedTemplate
                        ? `「${selectedTemplate.name}」スタイルで生成... (Shift+Enterで改行)`
                        : "画像の説明を入力... (Shift+Enterで改行)"
                    }
                    className="min-h-[52px] max-h-32 pr-12 resize-none text-sm rounded-xl border-border/60 focus-visible:ring-[var(--brand-300)]"
                    disabled={isGenerating}
                  />
                  <Button
                    size="sm"
                    className="absolute right-2 bottom-2 h-8 w-8 p-0 rounded-lg"
                    onClick={handleGenerate}
                    disabled={!prompt.trim() || isGenerating}
                  >
                    {isGenerating ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                <div className="flex items-center gap-3 mt-1.5 text-[10px] text-muted-foreground">
                  <span>
                    {aspectRatio !== "auto" ? aspectRatio : "自動比率"} ・{" "}
                    {imageSize}
                  </span>
                  {selectedTemplate && (
                    <span className="flex items-center gap-1">
                      <Layers className="h-2.5 w-2.5" />
                      {selectedTemplate.name}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </main>

          {/* RIGHT: Gallery */}
          {showRightPanel && (
            <aside className="w-72 shrink-0 border-l border-border/60 flex flex-col bg-muted/10">
              <div className="flex items-center justify-between px-3 py-2.5 border-b border-border/40">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  生成画像
                </span>
                <Badge
                  variant="secondary"
                  className="text-[10px] h-4 px-1.5"
                >
                  {generatedImages.length}
                </Badge>
              </div>
              <ScrollArea className="flex-1">
                {generatedImages.length === 0 ? (
                  <div className="py-16 text-center px-4">
                    <GalleryHorizontalEnd className="h-8 w-8 mx-auto text-muted-foreground/25 mb-2" />
                    <p className="text-xs text-muted-foreground">
                      生成された画像がここに表示されます
                    </p>
                  </div>
                ) : (
                  <div className="p-2 grid grid-cols-2 gap-1.5">
                    {generatedImages.map((msg) => (
                      <div
                        key={msg.id}
                        className="relative group rounded-lg overflow-hidden cursor-pointer border border-border/30 transition-all hover:ring-2 hover:ring-primary/30"
                        onClick={() =>
                          toProxyUrl(msg.image_url) && setLightboxSrc(toProxyUrl(msg.image_url))
                        }
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={toProxyUrl(msg.image_url)!}
                          alt="Generated"
                          className="w-full aspect-square object-cover"
                        />
                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
                        <div className="absolute bottom-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button
                            variant="secondary"
                            size="sm"
                            className="h-6 w-6 p-0 bg-white/90 shadow-sm"
                            asChild
                            onClick={(e) => e.stopPropagation()}
                          >
                            <a
                              href={toProxyUrl(msg.image_url)!}
                              download
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              <Download className="h-3 w-3" />
                            </a>
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </aside>
          )}
        </div>

        {/* Template Dialog */}
        <TemplateDialog
          open={templateDialogOpen}
          onOpenChange={setTemplateDialogOpen}
          template={editingTemplate}
          onSave={handleSaveTemplate}
          onUploadRef={uploadReference}
          onDeleteRef={deleteReference}
        />

        {/* Lightbox */}
        {lightboxSrc && (
          <Lightbox
            src={lightboxSrc}
            onClose={() => setLightboxSrc(null)}
          />
        )}
      </div>
    </TooltipProvider>
  );
}
