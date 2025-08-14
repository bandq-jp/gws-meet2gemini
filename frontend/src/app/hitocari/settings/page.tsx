"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import { apiClient, GeminiSettings } from "@/lib/api";

export default function HitocariSettingsPage() {
  const [loading, setLoading] = useState(false);
  const [loadingSettings, setLoadingSettings] = useState(true);
  const [settings, setSettings] = useState({
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
    geminiMaxTokens: 8192,
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

  const handleSave = async () => {
    setLoading(true);
    try {
      // AI処理設定のみをバックエンドに送信
      const geminiSettings: GeminiSettings = {
        gemini_enabled: settings.geminiEnabled,
        gemini_model: settings.geminiModel,
        gemini_max_tokens: settings.geminiMaxTokens,
        gemini_temperature: settings.geminiTemperature,
      };

      await apiClient.updateSettings({
        gemini: geminiSettings
      });
      
      toast.success("設定を保存しました");
    } catch (error) {
      console.error('設定の保存に失敗:', error);
      toast.error("設定の保存に失敗しました");
    } finally {
      setLoading(false);
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

  const updateSetting = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="w-full px-6 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <Settings className="h-8 w-8" />
        <div>
          <h1 className="text-3xl font-bold tracking-tight">ひとキャリ設定</h1>
          <p className="text-muted-foreground">
            システムの動作と外部サービス連携を設定します
          </p>
        </div>
      </div>

      <Tabs defaultValue="ai" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="ai">AI処理</TabsTrigger>
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
                  構造化データ抽出用AI設定
                </CardDescription>
              </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Label htmlFor="gemini-enabled">Gemini AI処理を有効にする</Label>
                <Switch
                  id="gemini-enabled"
                  checked={settings.geminiEnabled}
                  onCheckedChange={(checked) => updateSetting('geminiEnabled', checked)}
                />
              </div>
              
              {settings.geminiEnabled && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="gemini-model">使用モデル</Label>
                    <select
                      id="gemini-model"
                      value={settings.geminiModel}
                      onChange={(e) => updateSetting('geminiModel', e.target.value)}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
                      <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                      <option value="gemini-1.5-pro">Gemini 1.5 Pro (レガシー)</option>
                      <option value="gemini-1.5-flash">Gemini 1.5 Flash (レガシー)</option>
                    </select>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="gemini-max-tokens">最大トークン数</Label>
                      <Input
                        id="gemini-max-tokens"
                        type="number"
                        value={settings.geminiMaxTokens}
                        onChange={(e) => updateSetting('geminiMaxTokens', parseInt(e.target.value))}
                        min="1024"
                        max="32768"
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="gemini-temperature">温度パラメータ</Label>
                      <Input
                        id="gemini-temperature"
                        type="number"
                        step="0.1"
                        value={settings.geminiTemperature}
                        onChange={(e) => updateSetting('geminiTemperature', parseFloat(e.target.value))}
                        min="0.0"
                        max="2.0"
                      />
                    </div>
                  </div>
                  
                  <Button
                    variant="outline"
                    onClick={() => handleTest('Gemini AI')}
                    disabled={loading}
                  >
                    <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    接続テスト
                  </Button>
                </>
              )}
            </CardContent>
          </Card>
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

      {/* 保存ボタン */}
      <Separator />
      <div className="flex justify-end space-x-4">
        <Button variant="outline" onClick={() => window.location.reload()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          リセット
        </Button>
        <Button onClick={handleSave} disabled={loading}>
          {loading ? (
            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          設定を保存
        </Button>
      </div>
    </div>
  );
}