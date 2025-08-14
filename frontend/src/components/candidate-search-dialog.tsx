"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Search, Loader2, User, Mail, Building, X } from "lucide-react";
import { apiClient, ZohoCandidate } from "@/lib/api";

interface CandidateSearchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCandidateSelect: (candidate: ZohoCandidate) => void;
  selectedCandidate?: ZohoCandidate | null;
}

export function CandidateSearchDialog({
  open,
  onOpenChange,
  onCandidateSelect,
  selectedCandidate,
}: CandidateSearchDialogProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<ZohoCandidate[]>([]);
  const [searching, setSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setSearching(true);
    try {
      const results = await apiClient.searchZohoCandidates(searchQuery.trim(), 20);
      setSearchResults(results.items);
      setHasSearched(true);
    } catch (error) {
      console.error('Failed to search candidates:', error);
      setSearchResults([]);
      setHasSearched(true);
    } finally {
      setSearching(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleCandidateClick = (candidate: ZohoCandidate) => {
    onCandidateSelect(candidate);
    onOpenChange(false);
  };

  const clearSelection = () => {
    onCandidateSelect(null);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Search className="w-5 h-5" />
            求職者を検索
          </DialogTitle>
          <DialogDescription>
            Zoho CRM から求職者を検索して選択してください
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Current Selection */}
          {selectedCandidate && (
            <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg">
              <div className="flex items-start justify-between">
                <div>
                  <Label className="text-sm font-medium text-primary">
                    選択中の候補者
                  </Label>
                  <div className="mt-2 space-y-1">
                    <div className="font-medium">{selectedCandidate.candidate_name}</div>
                    <div className="text-sm text-muted-foreground">
                      ID: {selectedCandidate.candidate_id}
                    </div>
                    {selectedCandidate.candidate_email && (
                      <div className="text-sm text-muted-foreground">
                        {selectedCandidate.candidate_email}
                      </div>
                    )}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearSelection}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Search Input */}
          <div className="space-y-2">
            <Label htmlFor="search-input">求職者名で検索</Label>
            <div className="flex gap-2">
              <Input
                id="search-input"
                placeholder="例: 田中太郎、たなか、Tanaka..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={searching}
              />
              <Button 
                onClick={handleSearch} 
                disabled={!searchQuery.trim() || searching}
              >
                {searching ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              姓名の一部でも検索できます（漢字、ひらがな、カタカナ、ローマ字対応）
            </p>
          </div>

          {/* Search Results */}
          <div className="space-y-3">
            {hasSearched && (
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium">
                  検索結果 ({searchResults.length}件)
                </Label>
                {searchResults.length > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSearchResults([]);
                      setHasSearched(false);
                      setSearchQuery("");
                    }}
                  >
                    クリア
                  </Button>
                )}
              </div>
            )}

            <div className="max-h-96 overflow-y-auto space-y-2">
              {searching ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin mr-2" />
                  検索中...
                </div>
              ) : hasSearched && searchResults.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <User className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p className="font-medium">候補者が見つかりませんでした</p>
                  <p className="text-sm">
                    別の検索キーワードをお試しください
                  </p>
                </div>
              ) : (
                searchResults.map((candidate) => (
                  <Card
                    key={candidate.record_id}
                    className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
                      selectedCandidate?.record_id === candidate.record_id
                        ? "ring-2 ring-primary bg-primary/5"
                        : "hover:bg-muted/50"
                    }`}
                    onClick={() => handleCandidateClick(candidate)}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 space-y-2">
                          <div className="flex items-center gap-2">
                            <User className="w-4 h-4 text-muted-foreground" />
                            <span className="font-medium">
                              {candidate.candidate_name || "(名前未設定)"}
                            </span>
                            {selectedCandidate?.record_id === candidate.record_id && (
                              <Badge variant="default" className="text-xs">
                                選択中
                              </Badge>
                            )}
                          </div>
                          
                          <div className="space-y-1 text-sm text-muted-foreground">
                            <div className="flex items-center gap-2">
                              <Building className="w-3 h-3" />
                              <span>ID: {candidate.candidate_id}</span>
                            </div>
                            
                            {candidate.candidate_email && (
                              <div className="flex items-center gap-2">
                                <Mail className="w-3 h-3" />
                                <span>{candidate.candidate_email}</span>
                              </div>
                            )}
                            
                            <div className="text-xs">
                              Record ID: {candidate.record_id}
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              キャンセル
            </Button>
            {selectedCandidate && (
              <Button onClick={() => onOpenChange(false)}>
                {selectedCandidate.candidate_name} を選択
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}