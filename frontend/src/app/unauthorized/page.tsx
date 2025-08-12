import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ShieldX } from 'lucide-react';
import Link from 'next/link';

export default function UnauthorizedPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-50 to-red-100 p-4">
      <Card className="w-full max-w-md mx-auto">
        <CardHeader className="text-center">
          <div className="mx-auto w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-4">
            <ShieldX className="w-6 h-6 text-red-600" />
          </div>
          <CardTitle className="text-2xl text-red-700">
            アクセス権限がありません
          </CardTitle>
          <CardDescription className="text-red-600">
            このシステムは @bandq.jp ドメインのアカウントでのみご利用いただけます
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center space-y-4">
          <p className="text-sm text-muted-foreground">
            適切なアカウントでログインするか、システム管理者にお問い合わせください。
          </p>
          <div className="flex flex-col gap-2">
            <Button asChild variant="default">
              <Link href="/sign-in">
                別のアカウントでログイン
              </Link>
            </Button>
            <Button asChild variant="outline">
              <a href="mailto:support@bandq.jp">
                サポートに問い合わせ
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}