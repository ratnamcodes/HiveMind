import { NextResponse } from "next/server";
import { getChannels } from "@/lib/mock/data";

// GET /api/channels — list all channels (ops + incidents).
export async function GET() {
  return NextResponse.json(getChannels());
}
