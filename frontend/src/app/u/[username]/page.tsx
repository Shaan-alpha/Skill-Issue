import { Report } from "@/types";
import { ResultsView } from "@/components/results-view";
import { notFound } from "next/navigation";

async function getAnalysis(username: string): Promise<Report> {
  const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
  const res = await fetch(`${baseUrl}/analyze/${username}`, {
    cache: "no-store", // Ensure we get fresh data for each analysis
  });

  if (!res.ok) {
    if (res.status === 404) notFound();
    throw new Error("Failed to fetch analysis");
  }

  return res.json();
}

export default async function AnalysisPage({ 
  params 
}: { 
  params: Promise<{ username: string }> 
}) {
  const { username } = await params;
  
  try {
    const report = await getAnalysis(username);
    return <ResultsView report={report} />;
  } catch (error) {
    console.error(error);
    return (
      <div className="flex min-h-screen flex-col items-center justify-center space-y-4">
        <h1 className="text-2xl font-bold">Analysis Failed</h1>
        <p className="text-muted-foreground">Make sure the backend is running at {process.env.NEXT_PUBLIC_BACKEND_URL}</p>
        <a href="/" className="text-accent underline">Try again</a>
      </div>
    );
  }
}
