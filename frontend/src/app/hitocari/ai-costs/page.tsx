"use client";

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  apiClient, 
  type AiCostOverview, 
  type MeetingCostDetail, 
  type PricingInfo,
  ApiError 
} from '@/lib/api';
import { 
  DollarSign, 
  MessageSquare, 
  Activity, 
  Calculator,
  Clock,
  Zap,
  Info,
  TrendingUp
} from 'lucide-react';

interface AiCostsPageProps {}

export default function AiCostsPage({}: AiCostsPageProps) {
  const [overview, setOverview] = useState<AiCostOverview | null>(null);
  const [selectedMeetingDetail, setSelectedMeetingDetail] = useState<MeetingCostDetail | null>(null);
  const [pricingInfo, setPricingInfo] = useState<PricingInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    loadOverview();
    loadPricingInfo();
  }, []);

  const loadOverview = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getAiCostSummary();
      setOverview(data);
    } catch (err) {
      console.error('AIコスト概要取得エラー:', err);
      setError(err instanceof ApiError ? err.message : 'データの取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const loadPricingInfo = async () => {
    try {
      const data = await apiClient.getPricingInfo();
      setPricingInfo(data);
    } catch (err) {
      console.error('料金情報取得エラー:', err);
    }
  };

  const loadMeetingDetail = async (meetingId: string) => {
    try {
      setDetailLoading(true);
      const data = await apiClient.getMeetingCostDetail(meetingId);
      setSelectedMeetingDetail(data);
    } catch (err) {
      console.error('会議詳細取得エラー:', err);
      setError(err instanceof ApiError ? err.message : '詳細データの取得に失敗しました');
    } finally {
      setDetailLoading(false);
    }
  };

  const formatCurrency = (amount: string | number) => {
    const num = typeof amount === 'string' ? parseFloat(amount) : amount;
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 4,
      maximumFractionDigits: 6
    }).format(num);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('ja-JP').format(num);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ja-JP');
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">AIコスト</h1>
          <p className="text-muted-foreground">Gemini AI使用量とコスト分析</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-4 w-20 mb-2" />
                <Skeleton className="h-8 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
        
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">AIコスト</h1>
          <Card className="max-w-md mx-auto">
            <CardContent className="p-6">
              <p className="text-destructive mb-4">{error}</p>
              <Button onClick={loadOverview}>再試行</Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">AIコスト</h1>
        <p className="text-muted-foreground">
          Gemini AI使用量とコスト分析
          {overview?.last_updated && (
            <span className="ml-2 text-xs">
              最終更新: {formatDate(overview.last_updated)}
            </span>
          )}
        </p>
      </div>

      {/* 概要カード */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6 flex items-center">
            <DollarSign className="h-8 w-8 text-green-600 mr-3" />
            <div>
              <p className="text-sm font-medium text-muted-foreground">総コスト</p>
              <p className="text-2xl font-bold">
                {formatCurrency(overview?.summary.total_cost_usd || '0')}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6 flex items-center">
            <MessageSquare className="h-8 w-8 text-blue-600 mr-3" />
            <div>
              <p className="text-sm font-medium text-muted-foreground">処理済み会議</p>
              <p className="text-2xl font-bold">{formatNumber(overview?.summary.total_meetings || 0)}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6 flex items-center">
            <Activity className="h-8 w-8 text-purple-600 mr-3" />
            <div>
              <p className="text-sm font-medium text-muted-foreground">API呼び出し</p>
              <p className="text-2xl font-bold">{formatNumber(overview?.summary.total_api_calls || 0)}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6 flex items-center">
            <Zap className="h-8 w-8 text-orange-600 mr-3" />
            <div>
              <p className="text-sm font-medium text-muted-foreground">総トークン数</p>
              <p className="text-2xl font-bold">{formatNumber(overview?.summary.total_tokens || 0)}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* タブ */}
      <Tabs defaultValue="meetings" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="meetings">会議別コスト</TabsTrigger>
          <TabsTrigger value="breakdown">コスト内訳</TabsTrigger>
          <TabsTrigger value="pricing">料金体系</TabsTrigger>
        </TabsList>

        {/* 会議別コストタブ */}
        <TabsContent value="meetings" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 会議一覧 */}
            <Card>
              <CardHeader>
                <CardTitle>最近処理された会議</CardTitle>
                <CardDescription>AI処理を実行した会議とそのコスト</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {overview?.recent_meetings.map((meeting) => (
                    <div 
                      key={meeting.meeting_id}
                      className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted cursor-pointer transition-colors"
                      onClick={() => loadMeetingDetail(meeting.meeting_id)}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">
                          {meeting.meeting_title}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="outline" className="text-xs">
                            {formatNumber(meeting.api_calls_count)} API
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {formatNumber(meeting.total_tokens)} tokens
                          </Badge>
                          {meeting.note && (
                            <Badge variant="secondary" className="text-xs">
                              {meeting.note}
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatDate(meeting.created_at)}
                        </p>
                      </div>
                      <div className="text-right ml-2">
                        <p className="font-bold text-green-600">
                          {formatCurrency(meeting.total_cost)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* 会議詳細 */}
            <Card>
              <CardHeader>
                <CardTitle>会議詳細</CardTitle>
                <CardDescription>選択された会議のAPI呼び出し詳細</CardDescription>
              </CardHeader>
              <CardContent>
                {detailLoading ? (
                  <div className="space-y-3">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Skeleton key={i} className="h-16 w-full" />
                    ))}
                  </div>
                ) : selectedMeetingDetail ? (
                  <div className="space-y-4">
                    <div className="border-b pb-3">
                      <h3 className="font-semibold">{selectedMeetingDetail.meeting_title}</h3>
                      <div className="grid grid-cols-2 gap-4 mt-2 text-sm">
                        <div>
                          <span className="text-muted-foreground">総コスト: </span>
                          <span className="font-semibold text-green-600">
                            {formatCurrency(selectedMeetingDetail.summary.total_cost)}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">API呼び出し: </span>
                          <span className="font-semibold">
                            {formatNumber(selectedMeetingDetail.summary.api_calls_count)}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">入力トークン: </span>
                          <span className="font-semibold">
                            {formatNumber(selectedMeetingDetail.summary.total_prompt_tokens)}
                          </span>
                        </div>
                        <div>
                          <span className="text-muted-foreground">出力トークン: </span>
                          <span className="font-semibold">
                            {formatNumber(selectedMeetingDetail.summary.total_output_tokens)}
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      <h4 className="text-sm font-semibold">API呼び出し詳細</h4>
                      {selectedMeetingDetail.call_details.map((call) => (
                        <div key={call.id} className="p-2 border rounded text-xs">
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="font-medium">{call.group_name}</p>
                              <p className="text-muted-foreground">
                                {call.model} - {call.pricing_tier}
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="font-semibold text-green-600">
                                {formatCurrency(call.total_cost)}
                              </p>
                              <p className="text-muted-foreground">{call.latency_ms}ms</p>
                            </div>
                          </div>
                          <div className="flex gap-2 mt-1">
                            <Badge variant="outline" className="text-xs">
                              I: {formatNumber(call.prompt_tokens)}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              O: {formatNumber(call.output_tokens)}
                            </Badge>
                            {call.cached_tokens > 0 && (
                              <Badge variant="outline" className="text-xs">
                                C: {formatNumber(call.cached_tokens)}
                              </Badge>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="text-muted-foreground text-center py-8">
                    会議を選択すると詳細が表示されます
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* コスト内訳タブ */}
        <TabsContent value="breakdown" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-blue-600" />
                  入力コスト
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold text-blue-600">
                  {formatCurrency(overview?.cost_breakdown.input_cost || '0')}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  プロンプトトークン: {formatNumber(overview?.summary.total_prompt_tokens || 0)}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5 text-green-600" />
                  出力コスト
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold text-green-600">
                  {formatCurrency(overview?.cost_breakdown.output_cost || '0')}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  出力+思考トークン: {formatNumber(overview?.summary.total_output_tokens || 0)}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="h-5 w-5 text-purple-600" />
                  キャッシュコスト
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold text-purple-600">
                  {formatCurrency(overview?.cost_breakdown.cache_cost || '0')}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  キャッシュ活用時のみ発生
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>効率性メトリクス</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">1API呼び出し平均コスト</p>
                  <p className="text-lg font-bold">
                    {formatCurrency(overview?.summary.average_cost_per_call || '0')}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">1トークンあたりコスト</p>
                  <p className="text-lg font-bold">
                    {overview?.summary.total_tokens ? 
                      formatCurrency(parseFloat(overview.summary.total_cost_usd) / overview.summary.total_tokens) :
                      formatCurrency(0)
                    }
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 料金体系タブ */}
        <TabsContent value="pricing" className="space-y-4">
          {pricingInfo && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Calculator className="h-5 w-5" />
                    {pricingInfo.model} 料金体系
                  </CardTitle>
                  <CardDescription>100万トークンあたりの料金 ({pricingInfo.currency})</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <h3 className="font-semibold text-blue-600">入力トークン</h3>
                      <p>標準 (≤20万): ${pricingInfo.pricing_per_million_tokens.input.standard}</p>
                      <p>大容量 (&gt;20万): ${pricingInfo.pricing_per_million_tokens.input.high_volume}</p>
                    </div>
                    <div className="space-y-2">
                      <h3 className="font-semibold text-green-600">出力トークン</h3>
                      <p>標準 (≤20万): ${pricingInfo.pricing_per_million_tokens.output.standard}</p>
                      <p>大容量 (&gt;20万): ${pricingInfo.pricing_per_million_tokens.output.high_volume}</p>
                    </div>
                    <div className="space-y-2">
                      <h3 className="font-semibold text-purple-600">キャッシュ</h3>
                      <p>標準 (≤20万): ${pricingInfo.pricing_per_million_tokens.context_cache.standard}</p>
                      <p>大容量 (&gt;20万): ${pricingInfo.pricing_per_million_tokens.context_cache.high_volume}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Info className="h-5 w-5" />
                    重要な注意事項
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {pricingInfo.notes.map((note, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <span className="text-muted-foreground">•</span>
                        <span>{note}</span>
                      </li>
                    ))}
                  </ul>
                  
                  <div className="mt-4 p-4 bg-muted rounded-lg">
                    <h4 className="font-semibold mb-2">計算例</h4>
                    <p className="text-sm text-muted-foreground mb-2">
                      {pricingInfo.calculation_example.description}
                    </p>
                    <div className="text-sm space-y-1">
                      <p>入力コスト: ${pricingInfo.calculation_example.input_cost}</p>
                      <p>出力コスト: ${pricingInfo.calculation_example.output_cost}</p>
                      <p className="font-semibold">合計: ${pricingInfo.calculation_example.total_cost}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}