"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useUser } from "@clerk/nextjs";
import { useImageGen } from "@/hooks/use-image-gen";
import type {
  ImageGenTemplate,
  ImageGenMessage,
  ImageGenReference,
} from "@/lib/api";
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
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
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Loader2,
  GalleryHorizontalEnd,
  Pencil,
  Maximize2,
  Clock,
  FolderOpen,
  Camera,
  ArrowRight,
  Wand2,
  Info,
} from "lucide-react";
import { SidebarTrigger } from "@/components/ui/sidebar";
import toast from "react-hot-toast";
import { useIsMobile } from "@/hooks/use-mobile";

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

const LABEL_MAP: Record<string, string> = {
  person: "人物",
  object: "素材",
  style: "スタイル",
};

// ── Template Dialog (2-step: create then add images) ──

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
  onSave: (data: Partial<ImageGenTemplate>) => Promise<ImageGenTemplate | void>;
  onUploadRef: (
    templateId: string,
    file: File,
    label: string
  ) => Promise<ImageGenReference>;
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
  const [step, setStep] = useState<"info" | "refs">("info");
  const [createdTemplate, setCreatedTemplate] =
    useState<ImageGenTemplate | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  // The "working" template is either the passed-in one or the one we just created
  const workingTemplate = template || createdTemplate;

  useEffect(() => {
    if (open) {
      if (template) {
        setName(template.name || "");
        setDescription(template.description || "");
        setCategory(template.category || "custom");
        setAspectRatio(template.aspect_ratio || "auto");
        setImageSize(template.image_size || "1K");
        setSystemPrompt(template.system_prompt || "");
        setStep("info");
      } else {
        setName("");
        setDescription("");
        setCategory("custom");
        setAspectRatio("auto");
        setImageSize("1K");
        setSystemPrompt("");
        setStep("info");
        setCreatedTemplate(null);
      }
    }
  }, [template, open]);

  const handleSave = async () => {
    if (!name.trim()) return;
    setSaving(true);
    try {
      const result = await onSave({
        name: name.trim(),
        description: description.trim() || undefined,
        category,
        aspect_ratio: aspectRatio,
        image_size: imageSize,
        system_prompt: systemPrompt.trim() || undefined,
      });
      if (!template && result) {
        // New template created — move to step 2
        setCreatedTemplate(result as ImageGenTemplate);
        setStep("refs");
        toast.success("テンプレートを作成しました。リファレンス画像を追加できます。");
      } else {
        toast.success("テンプレートを更新しました");
      }
    } catch {
      toast.error("保存に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length || !workingTemplate?.id) return;
    setUploadingRef(true);
    try {
      for (const file of Array.from(files)) {
        await onUploadRef(workingTemplate.id, file, refLabel);
      }
      toast.success(`${files.length}枚追加しました`);
    } catch {
      toast.error("アップロードに失敗しました");
    } finally {
      setUploadingRef(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (!workingTemplate?.id) return;
    const files = Array.from(e.dataTransfer.files).filter((f) =>
      f.type.startsWith("image/")
    );
    if (!files.length) return;
    setUploadingRef(true);
    try {
      for (const file of files) {
        await onUploadRef(workingTemplate.id, file, refLabel);
      }
      toast.success(`${files.length}枚追加しました`);
    } catch {
      toast.error("アップロードに失敗しました");
    } finally {
      setUploadingRef(false);
    }
  };

  const refs = workingTemplate?.image_gen_references || [];
  const isNew = !template;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] flex flex-col p-0 gap-0 overflow-hidden">
        {/* Header */}
        <DialogHeader className="px-6 pt-6 pb-4 shrink-0">
          <DialogTitle className="text-base font-semibold tracking-tight">
            {template
              ? "テンプレートを編集"
              : step === "refs"
              ? "リファレンス画像を追加"
              : "新規テンプレート"}
          </DialogTitle>
          <DialogDescription className="text-xs">
            {step === "refs"
              ? "スタイルの基準となる画像をアップロードしてください（最大14枚）"
              : "画像生成のスタイルとパラメータを設定します"}
          </DialogDescription>
        </DialogHeader>

        {/* Step indicator for new templates */}
        {isNew && (
          <div className="px-6 pb-3 shrink-0">
            <div className="flex items-center gap-2 text-xs">
              <span
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full transition-colors ${
                  step === "info"
                    ? "bg-[var(--brand-400)] text-white"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                <span className="w-4 h-4 rounded-full bg-white/20 flex items-center justify-center text-[10px] font-bold">
                  1
                </span>
                基本情報
              </span>
              <ArrowRight className="h-3 w-3 text-muted-foreground/40" />
              <span
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full transition-colors ${
                  step === "refs"
                    ? "bg-[var(--brand-400)] text-white"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                <span className="w-4 h-4 rounded-full bg-white/20 flex items-center justify-center text-[10px] font-bold">
                  2
                </span>
                リファレンス画像
              </span>
            </div>
          </div>
        )}

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 pb-2">
          {step === "info" ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-[11px] font-medium text-muted-foreground">
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
                  <Label className="text-[11px] font-medium text-muted-foreground">
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

              <div className="space-y-1.5">
                <Label className="text-[11px] font-medium text-muted-foreground">
                  説明（任意）
                </Label>
                <Input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="このテンプレートの用途や特徴"
                  className="h-9"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-[11px] font-medium text-muted-foreground">
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
                  <Label className="text-[11px] font-medium text-muted-foreground">
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

              <div className="space-y-1.5">
                <Label className="text-[11px] font-medium text-muted-foreground">
                  システムプロンプト（任意）
                </Label>
                <Textarea
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  placeholder="画像生成時に常に適用するスタイル指示..."
                  className="min-h-[72px] text-sm resize-none"
                />
              </div>

              {/* If editing existing template, show ref section inline */}
              {template && (
                <>
                  <Separator />
                  <RefSection
                    refs={refs}
                    templateId={template.id}
                    refLabel={refLabel}
                    setRefLabel={setRefLabel}
                    uploadingRef={uploadingRef}
                    fileInputRef={fileInputRef}
                    isDragOver={isDragOver}
                    setIsDragOver={setIsDragOver}
                    handleFileSelect={handleFileSelect}
                    handleDrop={handleDrop}
                    onDeleteRef={onDeleteRef}
                  />
                </>
              )}
            </div>
          ) : (
            /* Step 2: Reference images */
            <RefSection
              refs={refs}
              templateId={workingTemplate?.id || ""}
              refLabel={refLabel}
              setRefLabel={setRefLabel}
              uploadingRef={uploadingRef}
              fileInputRef={fileInputRef}
              isDragOver={isDragOver}
              setIsDragOver={setIsDragOver}
              handleFileSelect={handleFileSelect}
              handleDrop={handleDrop}
              onDeleteRef={onDeleteRef}
            />
          )}
        </div>

        {/* Footer */}
        <div className="shrink-0 flex items-center justify-between gap-2 px-6 py-4 border-t border-border/40 bg-muted/20">
          {step === "refs" && isNew ? (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setStep("info")}
                className="text-xs"
              >
                基本情報に戻る
              </Button>
              <Button
                size="sm"
                onClick={() => onOpenChange(false)}
                className="text-xs"
              >
                完了
              </Button>
            </>
          ) : (
            <>
              <div />
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onOpenChange(false)}
                  className="text-xs"
                >
                  キャンセル
                </Button>
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={!name.trim() || saving}
                  className="text-xs gap-1.5"
                >
                  {saving && (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  )}
                  {template ? "更新" : "作成して次へ"}
                </Button>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ── Reference Image Section (shared between dialog steps) ──

function RefSection({
  refs,
  templateId,
  refLabel,
  setRefLabel,
  uploadingRef,
  fileInputRef,
  isDragOver,
  setIsDragOver,
  handleFileSelect,
  handleDrop,
  onDeleteRef,
}: {
  refs: ImageGenReference[];
  templateId: string;
  refLabel: string;
  setRefLabel: (v: string) => void;
  uploadingRef: boolean;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  isDragOver: boolean;
  setIsDragOver: (v: boolean) => void;
  handleFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleDrop: (e: React.DragEvent) => void;
  onDeleteRef: (refId: string, templateId: string) => Promise<void>;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-medium text-muted-foreground">
            リファレンス画像
          </span>
          <Badge
            variant="secondary"
            className="text-[10px] h-4 px-1.5 font-normal"
          >
            {refs.length}/14
          </Badge>
        </div>
        <div className="flex items-center gap-1.5">
          <Select value={refLabel} onValueChange={setRefLabel}>
            <SelectTrigger className="h-7 text-[11px] w-[88px]">
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
            className="h-7 text-[11px] gap-1"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadingRef || refs.length >= 14}
          >
            {uploadingRef ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Upload className="h-3 w-3" />
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

      <div
        onDrop={handleDrop}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        className={`rounded-lg border-2 border-dashed transition-all ${
          isDragOver
            ? "border-[var(--brand-300)] bg-[var(--brand-100)]/10"
            : "border-border/50 hover:border-border"
        } ${refs.length > 0 ? "p-2" : "p-6"}`}
      >
        {refs.length > 0 ? (
          <div className="grid grid-cols-3 sm:grid-cols-5 gap-1.5">
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
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors" />
                <div className="absolute top-0.5 right-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => onDeleteRef(ref.id, templateId)}
                    className="w-5 h-5 rounded-full bg-black/60 hover:bg-red-600 flex items-center justify-center transition-colors"
                  >
                    <X className="h-2.5 w-2.5 text-white" />
                  </button>
                </div>
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent px-1 pb-0.5 pt-3">
                  <span className="text-[8px] text-white/80 font-medium">
                    {LABEL_MAP[ref.label] || ref.label}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center">
            <div className="w-10 h-10 mx-auto rounded-xl bg-muted/80 flex items-center justify-center mb-2">
              <Camera className="h-4.5 w-4.5 text-muted-foreground/50" />
            </div>
            <p className="text-xs text-muted-foreground">
              ここに画像をドラッグ&ドロップ
            </p>
            <p className="text-[10px] text-muted-foreground/60 mt-0.5">
              または上の「追加」ボタンからファイルを選択
            </p>
          </div>
        )}
      </div>

      {refs.length > 0 && (
        <div className="flex items-start gap-1.5 text-[10px] text-muted-foreground/70">
          <Info className="h-3 w-3 shrink-0 mt-0.5" />
          <span>
            人物最大5枚、オブジェクト最大6枚。参照画像はスタイルの基準として生成時に使用されます。
          </span>
        </div>
      )}
    </div>
  );
}

// ── Lightbox ──

function Lightbox({ src, onClose }: { src: string; onClose: () => void }) {
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center cursor-pointer animate-in fade-in duration-200"
      onClick={onClose}
    >
      <button
        className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"
        onClick={onClose}
      >
        <X className="h-5 w-5 text-white" />
      </button>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt="Generated"
        className="max-w-[90vw] max-h-[90vh] object-contain rounded-lg shadow-2xl animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  );
}

// ── Helpers ──

function toProxyUrl(url: string | undefined | null): string {
  if (!url) return "";
  return url.replace(/^\/api\/v1\//, "/api/proxy/");
}

function formatTime(dateStr?: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" });
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("ja-JP", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ── Template Thumbnail ──

function TemplateThumbnail({
  template,
  size = "md",
}: {
  template: ImageGenTemplate;
  size?: "sm" | "md";
}) {
  const refs = template.image_gen_references || [];
  const dim = size === "sm" ? "w-9 h-9" : "w-11 h-11";

  if (refs.length === 0) {
    return (
      <div
        className={`${dim} shrink-0 rounded-lg bg-gradient-to-br from-muted to-muted/50 flex items-center justify-center`}
      >
        <ImageIcon className="h-4 w-4 text-muted-foreground/40" />
      </div>
    );
  }

  if (refs.length === 1) {
    return (
      <div className={`${dim} shrink-0 rounded-lg overflow-hidden bg-muted`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={getRefImageUrl(refs[0].storage_path)}
          alt=""
          className="w-full h-full object-cover"
        />
      </div>
    );
  }

  // Collage for 2+ refs
  const shown = refs.slice(0, 4);
  return (
    <div
      className={`${dim} shrink-0 rounded-lg overflow-hidden bg-muted grid ${
        shown.length <= 2 ? "grid-cols-2" : "grid-cols-2 grid-rows-2"
      } gap-[1px]`}
    >
      {shown.map((ref) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          key={ref.id}
          src={getRefImageUrl(ref.storage_path)}
          alt=""
          className="w-full h-full object-cover"
        />
      ))}
    </div>
  );
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
    usage,
    fetchUsage,
  } = useImageGen();

  const isMobile = useIsMobile();
  const [prompt, setPrompt] = useState("");
  const [aspectRatio, setAspectRatio] = useState("auto");
  const [imageSize, setImageSize] = useState("1K");
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(
    null
  );
  const [showLeftPanel, setShowLeftPanel] = useState(true);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] =
    useState<ImageGenTemplate | null>(null);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const [sidebarTab, setSidebarTab] = useState<string>("templates");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-hide panels on mobile
  useEffect(() => {
    if (isMobile) {
      setShowLeftPanel(false);
      setShowRightPanel(false);
    }
  }, [isMobile]);

  useEffect(() => {
    fetchTemplates();
    fetchSessions();
    fetchUsage();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error, setError]);

  const selectedTemplate = templates.find((t) => t.id === selectedTemplateId);

  const handleNewSession = useCallback(async () => {
    const email = user?.emailAddresses[0]?.emailAddress;
    const session = await createSession({
      template_id: selectedTemplateId || undefined,
      title: selectedTemplate?.name
        ? `${selectedTemplate.name} - ${new Date().toLocaleDateString("ja-JP")}`
        : `セッション - ${new Date().toLocaleDateString("ja-JP")}`,
      aspect_ratio: aspectRatio,
      image_size: imageSize,
      created_by: user?.id,
      created_by_email: email,
    });
    return session;
  }, [
    createSession,
    selectedTemplateId,
    selectedTemplate,
    aspectRatio,
    imageSize,
    user,
  ]);

  const quotaReached = usage?.remaining !== null && usage?.remaining !== undefined && usage.remaining <= 0;

  const handleGenerate = useCallback(async () => {
    if (!prompt.trim() || isGenerating || quotaReached) return;

    // セッション未作成の場合は先に作成し、返されたセッションIDを直接渡す
    // (React State更新は非同期のため、currentSession はまだ null の可能性がある)
    let sessionId = currentSession?.id;
    if (!sessionId) {
      const newSession = await handleNewSession();
      if (!newSession?.id) return;
      sessionId = newSession.id;
    }

    await generateImage(prompt.trim(), {
      aspect_ratio: aspectRatio !== "auto" ? aspectRatio : undefined,
      image_size: imageSize,
      sessionId,
    });
    setPrompt("");
    textareaRef.current?.focus();
  }, [
    prompt,
    isGenerating,
    quotaReached,
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
      return;
    } else {
      const email = user?.emailAddresses[0]?.emailAddress;
      const result = await createTemplate({
        ...data,
        name: data.name || "",
        created_by: user?.id,
        created_by_email: email,
      });
      setEditingTemplate(result);
      return result;
    }
  };

  const generatedImages = messages.filter(
    (m) => m.role === "assistant" && m.image_url
  );

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex flex-col h-[calc(100dvh-2rem)] font-[family-name:var(--font-geist-sans)]">
        {/* ── Header ── */}
        <header className="shrink-0 flex items-center gap-1.5 sm:gap-2 px-2 sm:px-4 py-2.5 border-b border-border/50 bg-background">
          {/* Mobile sidebar trigger */}
          <SidebarTrigger className="md:hidden shrink-0" />

          {/* Logo + title */}
          <div className="flex items-center gap-2 mr-1 sm:mr-3">
            <div className="flex items-center justify-center w-7 h-7 rounded-md bg-[linear-gradient(135deg,var(--brand-300),var(--brand-400))] text-white">
              <Wand2 className="h-3.5 w-3.5" />
            </div>
            <h1 className="text-sm font-semibold tracking-tight hidden sm:block">
              画像生成
            </h1>
          </div>

          <Separator orientation="vertical" className="h-4 hidden sm:block" />

          {/* Generation controls */}
          <div className="flex items-center gap-1.5 flex-1 min-w-0">
            {/* Aspect ratio */}
            <Select value={aspectRatio} onValueChange={setAspectRatio}>
              <SelectTrigger className="h-7 w-[72px] text-[11px] border-border/40">
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

            {/* Resolution toggle */}
            <div className="flex items-center rounded-md h-7 border border-border/40 overflow-hidden">
              {RESOLUTIONS.map((r) => (
                <button
                  key={r.value}
                  onClick={() => setImageSize(r.value)}
                  className={`px-2 h-full text-[11px] font-medium transition-all ${
                    imageSize === r.value
                      ? "bg-[var(--brand-400)] text-white"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>

            {/* Active template indicator - hidden on mobile */}
            {selectedTemplate && (
              <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded-md bg-[var(--brand-100)]/20 border border-[var(--brand-200)]/30 max-w-[180px]">
                <Layers className="h-3 w-3 text-[var(--brand-400)] shrink-0" />
                <span className="text-[11px] text-[var(--brand-400)] font-medium truncate">
                  {selectedTemplate.name}
                </span>
                <button
                  onClick={() => setSelectedTemplateId(null)}
                  className="shrink-0 hover:text-foreground transition-colors"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            )}
          </div>

          {/* Right actions */}
          <div className="flex items-center gap-1">
            {/* Usage quota badge */}
            {usage && !usage.is_unlimited && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <div
                    className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-[11px] font-medium ${
                      usage.remaining !== null && usage.remaining <= 0
                        ? "bg-destructive/10 border-destructive/30 text-destructive"
                        : usage.remaining !== null && usage.remaining <= Math.ceil(usage.limit * 0.2)
                        ? "bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400"
                        : "bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
                    }`}
                  >
                    <ImageIcon className="h-3 w-3" />
                    <span>{usage.used} / {usage.limit}</span>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  <p>月間画像生成: {usage.used} / {usage.limit}枚（{usage.period}）</p>
                  {usage.remaining !== null && usage.remaining <= 0 && (
                    <p className="text-destructive">上限に達しました。来月リセットされます。</p>
                  )}
                </TooltipContent>
              </Tooltip>
            )}

            <Button
              variant="outline"
              size="sm"
              className="h-7 text-[11px] gap-1"
              onClick={handleNewSession}
            >
              <Plus className="h-3 w-3" />
              <span className="hidden md:inline">新規セッション</span>
            </Button>

            <Separator orientation="vertical" className="h-4 mx-0.5" />

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className={`h-7 w-7 p-0 ${showLeftPanel ? "text-foreground" : "text-muted-foreground"}`}
                  onClick={() => setShowLeftPanel((v) => !v)}
                >
                  {showLeftPanel ? (
                    <PanelLeftClose className="h-3.5 w-3.5" />
                  ) : (
                    <PanelLeftOpen className="h-3.5 w-3.5" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="text-xs">
                サイドバー
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className={`h-7 w-7 p-0 ${showRightPanel ? "text-foreground" : "text-muted-foreground"}`}
                  onClick={() => setShowRightPanel((v) => !v)}
                >
                  {showRightPanel ? (
                    <PanelRightClose className="h-3.5 w-3.5" />
                  ) : (
                    <PanelRightOpen className="h-3.5 w-3.5" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="text-xs">
                ギャラリー
              </TooltipContent>
            </Tooltip>
          </div>
        </header>

        {/* ── Error Banner ── */}
        {error && (
          <div className="shrink-0 px-4 py-2 bg-destructive/8 border-b border-destructive/20 text-destructive text-xs flex items-center gap-2">
            <span className="flex-1">{error}</span>
            <button
              onClick={() => setError(null)}
              className="hover:bg-destructive/10 rounded p-0.5"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        )}

        {/* ── Main 3-Column Layout ── */}
        <div className="flex-1 flex min-h-0 overflow-hidden relative">
          {/* Mobile backdrop for sidebars */}
          {isMobile && (showLeftPanel || showRightPanel) && (
            <div
              className="absolute inset-0 z-10 bg-black/30"
              onClick={() => { setShowLeftPanel(false); setShowRightPanel(false); }}
            />
          )}

          {/* LEFT SIDEBAR - overlay on mobile, inline on desktop */}
          {showLeftPanel && (
            <aside className={`${isMobile ? "absolute inset-y-0 left-0 z-20 w-[280px] max-w-[85vw] shadow-xl" : "w-[272px] shrink-0"} border-r border-border/50 flex flex-col bg-background`}>
              <Tabs
                value={sidebarTab}
                onValueChange={setSidebarTab}
                className="flex flex-col flex-1 min-h-0 gap-0"
              >
                <div className="shrink-0 px-2 pt-2">
                  <TabsList className="w-full h-8">
                    <TabsTrigger
                      value="templates"
                      className="text-[11px] gap-1 flex-1"
                    >
                      <Layers className="h-3 w-3" />
                      テンプレート
                    </TabsTrigger>
                    <TabsTrigger
                      value="history"
                      className="text-[11px] gap-1 flex-1"
                    >
                      <Clock className="h-3 w-3" />
                      履歴
                    </TabsTrigger>
                  </TabsList>
                </div>

                {/* Templates Tab */}
                <TabsContent
                  value="templates"
                  className="flex-1 min-h-0 flex flex-col mt-0"
                >
                  <div className="shrink-0 flex items-center justify-between px-3 py-2">
                    <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                      {templates.length}件のテンプレート
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 text-[11px] gap-1 px-2"
                      onClick={() => {
                        setEditingTemplate(null);
                        setTemplateDialogOpen(true);
                      }}
                    >
                      <Plus className="h-3 w-3" />
                      新規
                    </Button>
                  </div>
                  <ScrollArea className="flex-1 min-h-0">
                    <div className="px-2 pb-2 space-y-0.5">
                      {templates.length === 0 && !isLoading && (
                        <div className="py-12 text-center">
                          <div className="w-12 h-12 mx-auto rounded-xl bg-muted flex items-center justify-center mb-3">
                            <FolderOpen className="h-5 w-5 text-muted-foreground/40" />
                          </div>
                          <p className="text-xs text-muted-foreground mb-2">
                            テンプレートがありません
                          </p>
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-xs h-7 gap-1"
                            onClick={() => {
                              setEditingTemplate(null);
                              setTemplateDialogOpen(true);
                            }}
                          >
                            <Plus className="h-3 w-3" />
                            最初のテンプレートを作成
                          </Button>
                        </div>
                      )}
                      {templates.map((t) => {
                        const refCount =
                          t.image_gen_references?.length || 0;
                        const isSelected = selectedTemplateId === t.id;
                        return (
                          <div
                            key={t.id}
                            role="button"
                            tabIndex={0}
                            onClick={() =>
                              setSelectedTemplateId(
                                isSelected ? null : t.id
                              )
                            }
                            onKeyDown={(e) => {
                              if (e.key === "Enter" || e.key === " ")
                                setSelectedTemplateId(
                                  isSelected ? null : t.id
                                );
                            }}
                            className={`w-full text-left rounded-lg p-2 transition-all group cursor-pointer ${
                              isSelected
                                ? "bg-[var(--brand-100)]/15 ring-1 ring-[var(--brand-300)]/25"
                                : "hover:bg-muted/60"
                            }`}
                          >
                            <div className="flex items-start gap-2.5">
                              <TemplateThumbnail template={t} />
                              <div className="flex-1 min-w-0 pt-0.5">
                                <p className="text-[13px] font-medium truncate leading-tight">
                                  {t.name}
                                </p>
                                <div className="flex items-center gap-1 mt-1 flex-wrap">
                                  <span className="text-[10px] text-muted-foreground">
                                    {
                                      CATEGORIES.find(
                                        (c) => c.value === t.category
                                      )?.label || t.category
                                    }
                                  </span>
                                  <span className="text-muted-foreground/30">
                                    ·
                                  </span>
                                  <span className="text-[10px] text-muted-foreground">
                                    {t.aspect_ratio || "auto"}{" "}
                                    {t.image_size || "1K"}
                                  </span>
                                  {refCount > 0 && (
                                    <>
                                      <span className="text-muted-foreground/30">
                                        ·
                                      </span>
                                      <span className="text-[10px] text-[var(--brand-400)]">
                                        {refCount}枚
                                      </span>
                                    </>
                                  )}
                                </div>
                              </div>
                              <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-0.5 pt-0.5">
                                <button
                                  className="h-6 w-6 rounded-md flex items-center justify-center hover:bg-muted transition-colors"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setEditingTemplate(t);
                                    setTemplateDialogOpen(true);
                                  }}
                                >
                                  <Pencil className="h-3 w-3 text-muted-foreground" />
                                </button>
                                <button
                                  className="h-6 w-6 rounded-md flex items-center justify-center hover:bg-destructive/10 transition-colors"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    if (confirm("このテンプレートを削除しますか？"))
                                      deleteTemplate(t.id);
                                  }}
                                >
                                  <Trash2 className="h-3 w-3 text-muted-foreground" />
                                </button>
                              </div>
                            </div>
                            {t.description && (
                              <p className="text-[11px] text-muted-foreground/70 mt-1 line-clamp-1 ml-[52px]">
                                {t.description}
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </ScrollArea>
                </TabsContent>

                {/* History Tab */}
                <TabsContent
                  value="history"
                  className="flex-1 min-h-0 flex flex-col mt-0"
                >
                  <div className="shrink-0 flex items-center justify-between px-3 py-2">
                    <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                      {sessions.length}件のセッション
                    </span>
                  </div>
                  <ScrollArea className="flex-1 min-h-0">
                    <div className="px-2 pb-2 space-y-0.5">
                      {sessions.length === 0 && !isLoading && (
                        <div className="py-12 text-center">
                          <div className="w-12 h-12 mx-auto rounded-xl bg-muted flex items-center justify-center mb-3">
                            <Clock className="h-5 w-5 text-muted-foreground/40" />
                          </div>
                          <p className="text-xs text-muted-foreground">
                            まだセッションがありません
                          </p>
                          <p className="text-[10px] text-muted-foreground/60 mt-1">
                            画像を生成すると履歴が保存されます
                          </p>
                        </div>
                      )}
                      {sessions.map((s) => {
                        const isCurrent = currentSession?.id === s.id;
                        return (
                          <button
                            key={s.id}
                            onClick={() => loadSession(s.id)}
                            className={`w-full text-left rounded-lg p-2.5 transition-all ${
                              isCurrent
                                ? "bg-[var(--brand-100)]/15 ring-1 ring-[var(--brand-300)]/25"
                                : "hover:bg-muted/60"
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <div
                                className={`w-2 h-2 rounded-full shrink-0 ${
                                  isCurrent
                                    ? "bg-[var(--brand-400)]"
                                    : "bg-muted-foreground/20"
                                }`}
                              />
                              <div className="flex-1 min-w-0">
                                <p className="text-[13px] font-medium truncate leading-tight">
                                  {s.title || "無題のセッション"}
                                </p>
                                <div className="flex items-center gap-1.5 mt-0.5">
                                  <span className="text-[10px] text-muted-foreground">
                                    {formatDate(s.created_at)}
                                  </span>
                                  {s.aspect_ratio && (
                                    <>
                                      <span className="text-muted-foreground/30">
                                        ·
                                      </span>
                                      <span className="text-[10px] text-muted-foreground">
                                        {s.aspect_ratio} {s.image_size}
                                      </span>
                                    </>
                                  )}
                                </div>
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </ScrollArea>
                </TabsContent>
              </Tabs>
            </aside>
          )}

          {/* CENTER: Chat Area */}
          <main className="flex-1 flex flex-col min-w-0 min-h-0 overflow-hidden">
            <ScrollArea className="flex-1 min-h-0">
              <div className="max-w-2xl mx-auto px-5 py-6 space-y-5">
                {/* Empty state */}
                {messages.length === 0 && !isGenerating && (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[var(--brand-100)]/30 to-[var(--brand-200)]/20 flex items-center justify-center mb-4">
                      <Sparkles className="h-6 w-6 text-[var(--brand-400)]" />
                    </div>
                    <h2 className="text-base font-semibold tracking-tight mb-1.5">
                      画像を生成しましょう
                    </h2>
                    <p className="text-sm text-muted-foreground max-w-sm leading-relaxed">
                      {selectedTemplate
                        ? `「${selectedTemplate.name}」テンプレートで画像を生成します`
                        : "プロンプトを入力するか、テンプレートを選択して画像を生成"}
                    </p>
                    {selectedTemplate &&
                      (selectedTemplate.image_gen_references?.length || 0) >
                        0 && (
                        <div className="mt-4 flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--brand-100)]/15 text-[var(--brand-400)]">
                          <Layers className="h-3.5 w-3.5" />
                          <span className="text-xs font-medium">
                            {selectedTemplate.image_gen_references?.length}
                            枚のリファレンス画像が適用されます
                          </span>
                        </div>
                      )}

                    {/* Quick prompt suggestions */}
                    <div className="flex flex-wrap gap-2 mt-6 max-w-md justify-center">
                      {[
                        "ブログのアイキャッチ画像を作成して",
                        "モダンなバナーデザイン",
                        "SNS用のビジュアル素材",
                      ].map((suggestion) => (
                        <button
                          key={suggestion}
                          onClick={() => setPrompt(suggestion)}
                          className="px-3 py-1.5 rounded-full border border-border/60 text-xs text-muted-foreground hover:text-foreground hover:border-border hover:bg-muted/30 transition-all"
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Messages */}
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${
                      msg.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    {msg.role === "user" ? (
                      <div className="max-w-[80%] bg-[var(--brand-400)] text-white rounded-2xl rounded-br-sm px-4 py-2.5">
                        <p className="text-sm leading-relaxed">
                          {msg.text_content}
                        </p>
                        <p className="text-[10px] opacity-40 mt-1 text-right">
                          {formatTime(msg.created_at)}
                        </p>
                      </div>
                    ) : (
                      <div className="max-w-[90%] space-y-2">
                        {msg.text_content && (
                          <div className="bg-muted/40 rounded-2xl rounded-bl-sm px-4 py-3 border border-border/30">
                            <p className="text-sm leading-relaxed text-foreground">
                              {msg.text_content}
                            </p>
                          </div>
                        )}
                        {toProxyUrl(msg.image_url) && (
                          <div className="relative group rounded-xl overflow-hidden border border-border/40 shadow-sm cursor-pointer">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                              src={toProxyUrl(msg.image_url)}
                              alt="Generated image"
                              className="w-full h-auto max-w-lg"
                              onClick={() =>
                                setLightboxSrc(toProxyUrl(msg.image_url))
                              }
                            />
                            {/* Hover overlay */}
                            <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                              <button
                                className="w-7 h-7 rounded-md bg-white/90 hover:bg-white flex items-center justify-center shadow-sm transition-colors"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setLightboxSrc(toProxyUrl(msg.image_url));
                                }}
                              >
                                <Maximize2 className="h-3.5 w-3.5 text-foreground" />
                              </button>
                              <a
                                href={toProxyUrl(msg.image_url)}
                                download
                                target="_blank"
                                rel="noopener noreferrer"
                                className="w-7 h-7 rounded-md bg-white/90 hover:bg-white flex items-center justify-center shadow-sm transition-colors"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <Download className="h-3.5 w-3.5 text-foreground" />
                              </a>
                            </div>
                            {/* Metadata bar */}
                            {msg.metadata && (
                              <div className="absolute bottom-0 left-0 right-0 px-3 py-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                                <div className="flex items-center gap-2 text-[10px] text-white/80">
                                  {String(
                                    (
                                      msg.metadata as Record<string, unknown>
                                    )?.aspect_ratio || ""
                                  ) && (
                                    <span>
                                      {String(
                                        (
                                          msg.metadata as Record<
                                            string,
                                            unknown
                                          >
                                        )?.aspect_ratio ?? ""
                                      )}
                                    </span>
                                  )}
                                  {String(
                                    (
                                      msg.metadata as Record<string, unknown>
                                    )?.image_size || ""
                                  ) && (
                                    <span>
                                      {String(
                                        (
                                          msg.metadata as Record<
                                            string,
                                            unknown
                                          >
                                        )?.image_size ?? ""
                                      )}
                                    </span>
                                  )}
                                  {!!(
                                    msg.metadata as Record<string, unknown>
                                  )?.latency_ms && (
                                    <span>
                                      {(
                                        Number(
                                          (
                                            msg.metadata as Record<
                                              string,
                                              unknown
                                            >
                                          )?.latency_ms ?? 0
                                        ) / 1000
                                      ).toFixed(1)}
                                      s
                                    </span>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}

                {/* Generating indicator */}
                {isGenerating && (
                  <div className="flex justify-start">
                    <div className="bg-muted/40 rounded-2xl rounded-bl-sm border border-border/30 px-5 py-3.5 flex items-center gap-3">
                      <div className="flex gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-[var(--brand-300)] animate-bounce [animation-delay:0ms]" />
                        <span className="w-1.5 h-1.5 rounded-full bg-[var(--brand-300)] animate-bounce [animation-delay:150ms]" />
                        <span className="w-1.5 h-1.5 rounded-full bg-[var(--brand-300)] animate-bounce [animation-delay:300ms]" />
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
            <div className="shrink-0 border-t border-border/50 bg-background px-4 py-3">
              <div className="max-w-2xl mx-auto">
                {/* Quota reached banner */}
                {quotaReached && usage && (
                  <div className="mb-2 flex items-center gap-2 px-3 py-2 rounded-lg bg-destructive/8 border border-destructive/20 text-destructive text-xs">
                    <ImageIcon className="h-3.5 w-3.5 shrink-0" />
                    <span>月間画像生成の上限（{usage.limit}枚）に達しました。来月1日にリセットされます。</span>
                  </div>
                )}
                <div className="relative rounded-xl border border-border/60 bg-background focus-within:ring-1 focus-within:ring-[var(--brand-300)]/50 focus-within:border-[var(--brand-300)]/40 transition-all">
                  <Textarea
                    ref={textareaRef}
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={
                      quotaReached
                        ? "月間生成上限に達しています"
                        : selectedTemplate
                        ? `「${selectedTemplate.name}」スタイルで生成...`
                        : "画像の説明を入力..."
                    }
                    className="min-h-[48px] max-h-28 pr-12 resize-none text-sm border-0 focus-visible:ring-0 focus-visible:ring-offset-0 bg-transparent"
                    disabled={isGenerating || quotaReached}
                  />
                  <Button
                    size="sm"
                    className="absolute right-2 bottom-2 h-8 w-8 p-0 rounded-lg bg-[var(--brand-400)] hover:bg-[var(--brand-400)]/90"
                    onClick={handleGenerate}
                    disabled={!prompt.trim() || isGenerating || quotaReached}
                  >
                    {isGenerating ? (
                      <Loader2 className="h-4 w-4 animate-spin text-white" />
                    ) : (
                      <Send className="h-4 w-4 text-white" />
                    )}
                  </Button>
                </div>
                <div className="flex items-center gap-2 mt-1.5 px-1 text-[10px] text-muted-foreground/60">
                  <span>Enterで送信 · Shift+Enterで改行</span>
                  <span>·</span>
                  <span>
                    {aspectRatio !== "auto" ? aspectRatio : "自動"} · {imageSize}
                  </span>
                </div>
              </div>
            </div>
          </main>

          {/* RIGHT: Gallery - overlay on mobile, inline on desktop */}
          {showRightPanel && (
            <aside className={`${isMobile ? "absolute inset-y-0 right-0 z-20 w-[280px] max-w-[85vw] shadow-xl" : "w-[280px] shrink-0"} border-l border-border/50 flex flex-col bg-background`}>
              <div className="shrink-0 flex items-center justify-between px-3 py-2.5 border-b border-border/40">
                <div className="flex items-center gap-2">
                  <GalleryHorizontalEnd className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                    生成画像
                  </span>
                </div>
                {generatedImages.length > 0 && (
                  <Badge
                    variant="secondary"
                    className="text-[10px] h-4 px-1.5 font-normal"
                  >
                    {generatedImages.length}
                  </Badge>
                )}
              </div>
              <ScrollArea className="flex-1 min-h-0">
                {generatedImages.length === 0 ? (
                  <div className="py-20 text-center px-4">
                    <div className="w-12 h-12 mx-auto rounded-xl bg-muted flex items-center justify-center mb-3">
                      <ImageIcon className="h-5 w-5 text-muted-foreground/30" />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      生成画像がここに表示されます
                    </p>
                  </div>
                ) : (
                  <div className="p-2 space-y-2">
                    {generatedImages.map((msg) => {
                      const meta = msg.metadata as
                        | Record<string, unknown>
                        | undefined;
                      return (
                        <div
                          key={msg.id}
                          className="group rounded-lg overflow-hidden border border-border/30 bg-background transition-all hover:shadow-md hover:border-border/60"
                        >
                          <div
                            className="relative cursor-pointer"
                            onClick={() =>
                              setLightboxSrc(toProxyUrl(msg.image_url))
                            }
                          >
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                              src={toProxyUrl(msg.image_url)!}
                              alt="Generated"
                              className="w-full h-auto"
                            />
                            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
                            <div className="absolute top-1.5 right-1.5 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                              <button
                                className="w-6 h-6 rounded-md bg-white/90 hover:bg-white flex items-center justify-center shadow-sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setLightboxSrc(toProxyUrl(msg.image_url));
                                }}
                              >
                                <Maximize2 className="h-3 w-3" />
                              </button>
                              <a
                                href={toProxyUrl(msg.image_url)!}
                                download
                                target="_blank"
                                rel="noopener noreferrer"
                                className="w-6 h-6 rounded-md bg-white/90 hover:bg-white flex items-center justify-center shadow-sm"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <Download className="h-3 w-3" />
                              </a>
                            </div>
                          </div>
                          {/* Metadata footer */}
                          <div className="px-2.5 py-1.5 border-t border-border/20">
                            <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                              <div className="flex items-center gap-1.5">
                                {!!meta?.aspect_ratio && (
                                  <span>{String(meta.aspect_ratio)}</span>
                                )}
                                {!!meta?.image_size && (
                                  <span>{String(meta.image_size)}</span>
                                )}
                              </div>
                              <span>{formatTime(msg.created_at)}</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </ScrollArea>
            </aside>
          )}
        </div>

        {/* Template Dialog */}
        <TemplateDialog
          open={templateDialogOpen}
          onOpenChange={(v) => {
            setTemplateDialogOpen(v);
            if (!v) setEditingTemplate(null);
          }}
          template={editingTemplate}
          onSave={handleSaveTemplate}
          onUploadRef={uploadReference}
          onDeleteRef={deleteReference}
        />

        {/* Lightbox */}
        {lightboxSrc && (
          <Lightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
        )}
      </div>
    </TooltipProvider>
  );
}
