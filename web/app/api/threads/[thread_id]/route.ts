import { NextResponse } from "next/server";
import { getThread } from "@/lib/mock/data";

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ thread_id: string }> },
) {
  const { thread_id } = await params;
  const thread = getThread(thread_id);
  if (!thread) {
    return NextResponse.json({ error: "thread not found" }, { status: 404 });
  }
  return NextResponse.json(thread);
}
