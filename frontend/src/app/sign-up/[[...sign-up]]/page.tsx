import { SignUp } from '@clerk/nextjs';

export default function Page() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">b&q Hub</h1>
          <p className="text-muted-foreground">
            社内統合管理システムにサインアップ
          </p>
        </div>
        <SignUp 
          appearance={{
            elements: {
              rootBox: "mx-auto",
              card: "shadow-lg border-0 bg-white/95 backdrop-blur-sm",
            }
          }}
          signInUrl="/sign-in"
          redirectUrl="/"
        />
        <div className="text-center mt-6 text-sm text-muted-foreground">
          <p>@bandq.jp ドメインのアカウントでのみサインアップ可能です</p>
        </div>
      </div>
    </div>
  );
}