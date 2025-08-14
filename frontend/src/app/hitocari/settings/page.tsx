"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import {
  Settings,
  Database,
  Cloud,
  Bell,
  Shield,
  Save,
  RefreshCw,
  Key,
  Server,
  Mail,
} from "lucide-react";
import toast from "react-hot-toast";
import { apiClient, CustomSchema, SchemaField } from "@/lib/api";
import { SidebarTrigger } from "@/components/ui/sidebar";

// 設定状態の型を明確化
interface SettingsState {
  // Google Drive設定
  googleDriveEnabled: boolean;
  googleDriveAccount: string;
  googleDriveFolder: string;

  // Zoho CRM設定
  zohoEnabled: boolean;
  zohoClientId: string;
  zohoClientSecret: string;
  zohoRefreshToken: string;
  zohoModule: string;
  zohoNameField: string;
  zohoIdField: string;

  // AI処理設定
  geminiEnabled: boolean;
  geminiModel: string;
  geminiMaxTokens: number;
  geminiTemperature: number;

  // 通知設定
  emailNotifications: boolean;
  slackNotifications: boolean;
  notificationEmail: string;

  // 自動処理設定
  autoCollectMeetings: boolean;
  autoProcessStructured: boolean;
  collectInterval: number; // minutes
}

export default function HitocariSettingsPage() {
  const [loading, setLoading] = useState(false);
  const [loadingSettings, setLoadingSettings] = useState(true);
  
  // カスタムスキーマ関連の状態
  const [customSchemas, setCustomSchemas] = useState<CustomSchema[]>([]);
  const [loadingSchemas, setLoadingSchemas] = useState(false);
  const [selectedSchema, setSelectedSchema] = useState<CustomSchema | null>(null);
  const [defaultSchemaDefinition, setDefaultSchemaDefinition] = useState<CustomSchema | null>(null);
  const [loadingDefaultDefinition, setLoadingDefaultDefinition] = useState(false);
  const [settings, setSettings] = useState<SettingsState>({
    // Google Drive設定
    googleDriveEnabled: true,
    googleDriveAccount: "admin@bandq.jp",
    googleDriveFolder: "Meet Recordings",
    
    // Zoho CRM設定
    zohoEnabled: false,
    zohoClientId: "",
    zohoClientSecret: "",
    zohoRefreshToken: "",
    zohoModule: "CustomModule1",
    zohoNameField: "求職者名",
    zohoIdField: "求職者ID",
    
    // AI処理設定
    geminiEnabled: true,
    geminiModel: "gemini-2.5-pro",
    geminiMaxTokens: 20000,
    geminiTemperature: 0.1,
    
    // 通知設定
    emailNotifications: true,
    slackNotifications: false,
    notificationEmail: "admin@bandq.jp",
    
    // 自動処理設定
    autoCollectMeetings: false,
    autoProcessStructured: false,
    collectInterval: 60, // minutes
  });

  // バックエンドから設定を読み込み
  useEffect(() => {
    loadSettings();
    loadSchemas();
    loadDefaultSchemaDefinition();
  }, []);

  const loadSettings = async () => {
    try {
      setLoadingSettings(true);
      const response = await apiClient.getSettings();
      
      setSettings(prev => ({
        ...prev,
        geminiEnabled: response.gemini.gemini_enabled,
        geminiModel: response.gemini.gemini_model,
        geminiMaxTokens: response.gemini.gemini_max_tokens,
        geminiTemperature: response.gemini.gemini_temperature,
      }));
    } catch (error) {
      console.error('設定の読み込みに失敗:', error);
      toast.error('設定の読み込みに失敗しました');
    } finally {
      setLoadingSettings(false);
    }
  };

  const loadSchemas = async () => {
    try {
      setLoadingSchemas(true);
      const schemas = await apiClient.getAllSchemas();
      setCustomSchemas(schemas);
    } catch (error) {
      console.error('スキーマの読み込みに失敗:', error);
      toast.error('スキーマの読み込みに失敗しました');
    } finally {
      setLoadingSchemas(false);
    }
  };

  const loadDefaultSchemaDefinition = async () => {
    try {
      setLoadingDefaultDefinition(true);
      const schema = await apiClient.getDefaultSchemaDefinition();
      setDefaultSchemaDefinition(schema);
      // デフォルト表示としてシステム定義スキーマを選択
      if (!selectedSchema) {
        setSelectedSchema(schema);
      }
    } catch (error) {
      console.error('デフォルトスキーマ定義の読み込みに失敗:', error);
      // ここではトーストは控えめに（必須ではないため）
    } finally {
      setLoadingDefaultDefinition(false);
    }
  };


  const handleTest = async (service: string) => {
    setLoading(true);
    try {
      // TODO: サービス接続テスト
      await new Promise(resolve => setTimeout(resolve, 1000)); // Mock delay
      toast.success(`${service}の接続テストが成功しました`);
    } catch (error) {
      toast.error(`${service}の接続テストに失敗しました`);
    } finally {
      setLoading(false);
    }
  };

  const updateSetting = <K extends keyof SettingsState>(key: K, value: SettingsState[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="w-full px-6 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <SidebarTrigger className="md:hidden" />
        <Settings className="h-8 w-8" />
        <div>
          <h1 className="text-3xl font-bold tracking-tight">ひとキャリ設定</h1>
          <p className="text-muted-foreground">
            システムの動作と外部サービス連携を設定します
          </p>
        </div>
      </div>

      <Tabs defaultValue="ai" className="space-y-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="ai">AI処理</TabsTrigger>
          <TabsTrigger value="schemas">スキーマ管理</TabsTrigger>
          <TabsTrigger value="integrations">外部連携</TabsTrigger>
          <TabsTrigger value="notifications">通知</TabsTrigger>
          <TabsTrigger value="automation">自動化</TabsTrigger>
        </TabsList>

        {/* 外部連携設定 */}
        <TabsContent value="integrations" className="space-y-6">
          {/* Google Drive設定 */}
          <Card className="opacity-60">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Cloud className="h-5 w-5" />
                <span>Google Drive連携</span>
                <span className="text-xs bg-orange-100 text-orange-600 px-2 py-1 rounded">開発中</span>
              </CardTitle>
              <CardDescription>
                議事録の自動収集用Google Drive設定
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Label htmlFor="google-drive-enabled" className="text-muted-foreground">Google Drive連携を有効にする</Label>
                <Switch
                  id="google-drive-enabled"
                  checked={settings.googleDriveEnabled}
                  disabled={true}
                />
              </div>
              
              {settings.googleDriveEnabled && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="google-account" className="text-muted-foreground">Googleアカウント</Label>
                    <Input
                      id="google-account"
                      value={settings.googleDriveAccount}
                      disabled={true}
                      placeholder="admin@bandq.jp"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="google-folder" className="text-muted-foreground">監視フォルダ名</Label>
                    <Input
                      id="google-folder"
                      value={settings.googleDriveFolder}
                      disabled={true}
                      placeholder="Meet Recordings"
                    />
                  </div>
                  
                  <Button
                    variant="outline"
                    disabled={true}
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    接続テスト
                  </Button>
                </>
              )}
            </CardContent>
          </Card>

          {/* Zoho CRM設定 */}
          <Card className="opacity-60">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Database className="h-5 w-5" />
                <span>Zoho CRM連携</span>
                <span className="text-xs bg-orange-100 text-orange-600 px-2 py-1 rounded">開発中</span>
              </CardTitle>
              <CardDescription>
                候補者データベース連携設定
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Label htmlFor="zoho-enabled" className="text-muted-foreground">Zoho CRM連携を有効にする</Label>
                <Switch
                  id="zoho-enabled"
                  checked={settings.zohoEnabled}
                  disabled={true}
                />
              </div>
              
              {settings.zohoEnabled && (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="zoho-client-id" className="text-muted-foreground">クライアントID</Label>
                      <Input
                        id="zoho-client-id"
                        type="password"
                        value={settings.zohoClientId}
                        disabled={true}
                        placeholder="Client ID"
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="zoho-client-secret" className="text-muted-foreground">クライアントシークレット</Label>
                      <Input
                        id="zoho-client-secret"
                        type="password"
                        value={settings.zohoClientSecret}
                        disabled={true}
                        placeholder="Client Secret"
                      />
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="zoho-refresh-token" className="text-muted-foreground">リフレッシュトークン</Label>
                    <Input
                      id="zoho-refresh-token"
                      type="password"
                      value={settings.zohoRefreshToken}
                      disabled={true}
                      placeholder="Refresh Token"
                    />
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="zoho-module">モジュール名</Label>
                      <Input
                        id="zoho-module"
                        value={settings.zohoModule}
                        onChange={(e) => updateSetting('zohoModule', e.target.value)}
                        placeholder="CustomModule1"
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="zoho-name-field">名前フィールド</Label>
                      <Input
                        id="zoho-name-field"
                        value={settings.zohoNameField}
                        onChange={(e) => updateSetting('zohoNameField', e.target.value)}
                        placeholder="求職者名"
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="zoho-id-field">IDフィールド</Label>
                      <Input
                        id="zoho-id-field"
                        value={settings.zohoIdField}
                        onChange={(e) => updateSetting('zohoIdField', e.target.value)}
                        placeholder="求職者ID"
                      />
                    </div>
                  </div>
                  
                  <Button
                    variant="outline"
                    disabled={true}
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    接続テスト
                  </Button>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* AI処理設定 */}
        <TabsContent value="ai" className="space-y-6">
          {loadingSettings ? (
            <Card>
              <CardContent className="flex items-center justify-center py-12">
                <div className="text-center">
                  <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4" />
                  <p className="text-muted-foreground">設定を読み込み中...</p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Key className="h-5 w-5" />
                  <span>Gemini AI設定</span>
                </CardTitle>
                <CardDescription>
                  構造化データ抽出用AI設定（読み取り専用）
                </CardDescription>
              </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Label htmlFor="gemini-enabled" className="text-muted-foreground">Gemini AI処理を有効にする</Label>
                <Switch
                  id="gemini-enabled"
                  checked={settings.geminiEnabled}
                  disabled={true}
                />
              </div>
              
              {settings.geminiEnabled && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="gemini-model" className="text-muted-foreground">使用モデル</Label>
                    <Input
                      id="gemini-model"
                      value={settings.geminiModel}
                      disabled={true}
                      className="bg-muted"
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="gemini-max-tokens" className="text-muted-foreground">最大トークン数</Label>
                      <Input
                        id="gemini-max-tokens"
                        type="number"
                        value={settings.geminiMaxTokens}
                        disabled={true}
                        className="bg-muted"
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="gemini-temperature" className="text-muted-foreground">温度パラメータ</Label>
                      <Input
                        id="gemini-temperature"
                        type="number"
                        step="0.1"
                        value={settings.geminiTemperature}
                        disabled={true}
                        className="bg-muted"
                      />
                    </div>
                  </div>
                  
                  <Button
                    variant="outline"
                    disabled={true}
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    接続テスト
                  </Button>
                </>
              )}
            </CardContent>
          </Card>
          )}
        </TabsContent>

        {/* スキーマ管理 */}
        <TabsContent value="schemas" className="space-y-6">
          {loadingSchemas ? (
            <Card>
              <CardContent className="flex items-center justify-center py-12">
                <div className="text-center">
                  <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4" />
                  <p className="text-muted-foreground">スキーマを読み込み中...</p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-6">
              {/* コード定義のデフォルトスキーマ（常に表示） */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Database className="h-5 w-5" />
                    <span>システム・デフォルトスキーマ（コード定義）</span>
                  </CardTitle>
                  <CardDescription>
                    backend/app/domain/schemas/structured_extraction_schema.py を動的に解析した結果
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {loadingDefaultDefinition ? (
                    <div className="flex items-center justify-center py-6 text-muted-foreground text-sm">
                      <RefreshCw className="h-4 w-4 animate-spin mr-2" /> 読み込み中...
                    </div>
                  ) : defaultSchemaDefinition ? (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="space-y-1">
                          <h4 className="font-medium">{defaultSchemaDefinition.name}</h4>
                          <p className="text-sm text-muted-foreground">{defaultSchemaDefinition.description}</p>
                          <div className="text-xs text-muted-foreground">
                            {defaultSchemaDefinition.fields.length} フィールド • {defaultSchemaDefinition.schema_groups.length} グループ
                          </div>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedSchema(defaultSchemaDefinition)}
                        >
                          詳細を表示
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="text-sm text-muted-foreground">デフォルトスキーマを取得できませんでした。</div>
                  )}
                </CardContent>
              </Card>

              {/* スキーマ一覧 */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Database className="h-5 w-5" />
                    <span>カスタムスキーマ一覧</span>
                  </CardTitle>
                  <CardDescription>
                    構造化データ抽出に使用するスキーマの管理
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {customSchemas.length === 0 ? (
                    <div className="text-center py-8">
                      <p className="text-muted-foreground mb-4">カスタムスキーマが見つかりません（必要に応じて初期化してください）</p>
                      <Button onClick={() => apiClient.initializeDefaultSchema().then(loadSchemas)}>
                        デフォルトスキーマを初期化
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {customSchemas.map((schema) => (
                        <div
                          key={schema.id}
                          className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                            selectedSchema?.id === schema.id 
                              ? 'border-primary bg-primary/5' 
                              : 'hover:border-muted-foreground'
                          }`}
                          onClick={() => setSelectedSchema(schema)}
                        >
                          <div className="flex items-start justify-between">
                            <div className="space-y-1">
                              <div className="flex items-center space-x-2">
                                <h4 className="font-medium">{schema.name}</h4>
                                {schema.is_default && (
                                  <Badge variant="default">デフォルト</Badge>
                                )}
                                {!schema.is_active && (
                                  <Badge variant="secondary">非アクティブ</Badge>
                                )}
                              </div>
                              <p className="text-sm text-muted-foreground">
                                {schema.description || 'スキーマの説明がありません'}
                              </p>
                              <div className="text-xs text-muted-foreground">
                                {schema.fields.length} フィールド • {schema.schema_groups.length} グループ
                              </div>
                            </div>
                            <div className="flex items-center space-x-2">
                              {!schema.is_default && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    if (schema.id) {
                                      apiClient.setDefaultSchema(schema.id)
                                        .then(() => {
                                          toast.success('デフォルトスキーマを設定しました');
                                          loadSchemas();
                                        })
                                        .catch(() => toast.error('デフォルトスキーマの設定に失敗しました'));
                                    }
                                  }}
                                >
                                  デフォルトに設定
                                </Button>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* スキーマ詳細表示（選択したスキーマ or デフォルト） */}
              {selectedSchema && (
                <Card>
                  <CardHeader>
                    <CardTitle>スキーマ詳細: {selectedSchema.name}</CardTitle>
                    <CardDescription>
                      フィールドとグループの詳細情報
                  </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-6">
                      {selectedSchema.schema_groups.map((group, groupIndex) => {
                        const groupFields = selectedSchema.fields.filter(f => f.group_name === group.name);
                        if (groupFields.length === 0) return null;

                        return (
                          <div key={groupIndex} className="space-y-3">
                            <h4 className="text-base font-semibold text-foreground border-b pb-2">
                              {group.name}
                            </h4>
                            <div className="grid gap-3">
                              {groupFields.map((field, fieldIndex) => (
                                <div key={fieldIndex} className="border rounded-lg p-3">
                                  <div className="flex items-start justify-between mb-2">
                                    <div>
                                      <h5 className="font-medium text-sm">{field.field_label}</h5>
                                      <p className="text-xs text-muted-foreground">キー: {field.field_key}</p>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                      <Badge variant="outline" className="text-xs">
                                        {field.field_type}
                                        {field.array_item_type && `<${field.array_item_type}>`}
                                      </Badge>
                                      {field.is_required && (
                                        <Badge variant="destructive" className="text-xs">必須</Badge>
                                      )}
                                    </div>
                                  </div>
                                  {field.field_description && (
                                    <p className="text-xs text-muted-foreground mb-2">
                                      {field.field_description}
                                    </p>
                                  )}
                                  {field.enum_options.length > 0 && (
                                    <div className="mt-2">
                                      <p className="text-xs font-medium text-muted-foreground mb-1">選択肢:</p>
                                      <div className="flex flex-wrap gap-1">
                                        {field.enum_options.map((option, optionIndex) => (
                                          <Badge key={optionIndex} variant="secondary" className="text-xs">
                                            {option.value}
                                          </Badge>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </TabsContent>

        {/* 通知設定 */}
        <TabsContent value="notifications" className="space-y-6">
          <Card className="opacity-60">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Bell className="h-5 w-5" />
                <span>通知設定</span>
                <span className="text-xs bg-orange-100 text-orange-600 px-2 py-1 rounded">開発中</span>
              </CardTitle>
              <CardDescription>
                処理完了やエラー時の通知設定
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Label htmlFor="email-notifications" className="text-muted-foreground">メール通知</Label>
                <Switch
                  id="email-notifications"
                  checked={settings.emailNotifications}
                  disabled={true}
                />
              </div>
              
              {settings.emailNotifications && (
                <div className="space-y-2">
                  <Label htmlFor="notification-email">通知先メールアドレス</Label>
                  <Input
                    id="notification-email"
                    type="email"
                    value={settings.notificationEmail}
                    onChange={(e) => updateSetting('notificationEmail', e.target.value)}
                    placeholder="admin@bandq.jp"
                  />
                </div>
              )}
              
              <div className="flex items-center justify-between">
                <Label htmlFor="slack-notifications" className="text-muted-foreground">Slack通知</Label>
                <Switch
                  id="slack-notifications"
                  checked={settings.slackNotifications}
                  disabled={true}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 自動化設定 */}
        <TabsContent value="automation" className="space-y-6">
          <Card className="opacity-60">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Server className="h-5 w-5" />
                <span>自動化設定</span>
                <span className="text-xs bg-orange-100 text-orange-600 px-2 py-1 rounded">開発中</span>
              </CardTitle>
              <CardDescription>
                定期実行とバッチ処理の設定
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Label htmlFor="auto-collect" className="text-muted-foreground">議事録の自動収集</Label>
                <Switch
                  id="auto-collect"
                  checked={settings.autoCollectMeetings}
                  disabled={true}
                />
              </div>
              
              {settings.autoCollectMeetings && (
                <div className="space-y-2">
                  <Label htmlFor="collect-interval">収集間隔（分）</Label>
                  <Input
                    id="collect-interval"
                    type="number"
                    value={settings.collectInterval}
                    onChange={(e) => updateSetting('collectInterval', parseInt(e.target.value))}
                    min="5"
                    max="1440"
                  />
                </div>
              )}
              
              <div className="flex items-center justify-between">
                <Label htmlFor="auto-process" className="text-muted-foreground">構造化の自動処理</Label>
                <Switch
                  id="auto-process"
                  checked={settings.autoProcessStructured}
                  disabled={true}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* リフレッシュボタン */}
      <Separator />
      <div className="flex justify-end space-x-4">
        <Button variant="outline" onClick={() => window.location.reload()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          リフレッシュ
        </Button>
      </div>
    </div>
  );
}
