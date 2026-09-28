import { router } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { SendIcon } from '@/components/icons';
import { Orb } from '@/components/Orb';
import { Body, Button, Card, Field, Micro, Serif, Tag } from '@/components/ui';
import {
  fallbackOrganize,
  fallbackReply,
  guardianReply,
  OPENING,
  ORGANIZE_ASK,
  organizeOrb,
  type OrganizedOrb,
} from '@/lib/guardian';
import type { ChatTurn } from '@/lib/state';
import { useStore } from '@/lib/store';
import { colors, domainColor, domainLabel, fonts, radius, type Domain } from '@/theme';

export default function Onboarding() {
  const insets = useSafeAreaInsets();
  const { state, update } = useStore();
  const [chat, setChat] = useState<ChatTurn[]>(() =>
    state.chat.length ? state.chat : [{ role: 'assistant', content: OPENING }],
  );
  const [draft, setDraft] = useState('');
  const [thinking, setThinking] = useState(false);
  const [offline, setOffline] = useState(false);
  const [declined, setDeclined] = useState(false);
  const [orb, setOrb] = useState<OrganizedOrb | null>(null);
  const [vision, setVision] = useState('');
  const scroll = useRef<ScrollView>(null);

  // Keep the conversation so a reload mid-onboarding picks up where it left off.
  useEffect(() => {
    update((s) => ({ ...s, chat }));
  }, [chat, update]);

  useEffect(() => {
    const id = setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 50);
    return () => clearTimeout(id);
  }, [chat, thinking, orb]);

  const last = chat[chat.length - 1];
  const asking = !declined && last?.role === 'assistant' && last.content.includes(ORGANIZE_ASK);

  async function send() {
    const text = draft.trim();
    if (!text || thinking) return;
    const next: ChatTurn[] = [...chat, { role: 'user', content: text }];
    setDraft('');
    setDeclined(false);
    setChat(next);
    setThinking(true);
    let reply: string;
    if (offline) {
      await new Promise((r) => setTimeout(r, 900));
      reply = fallbackReply(next);
    } else {
      try {
        reply = await guardianReply(next);
      } catch {
        setOffline(true);
        reply = fallbackReply(next);
      }
    }
    setChat([...next, { role: 'assistant', content: reply }]);
    setThinking(false);
  }

  async function organize() {
    setThinking(true);
    let result: OrganizedOrb;
    try {
      result = offline ? fallbackOrganize(chat) : await organizeOrb(chat);
    } catch {
      result = fallbackOrganize(chat);
    }
    setOrb(result);
    setVision(result.vision);
    setThinking(false);
  }

  function enter(skip = false) {
    update((s) => ({
      ...s,
      profile: {
        ...s.profile,
        onboarded: true,
        name: orb?.name ?? s.profile.name,
        vision: skip ? s.profile.vision : vision.trim() || orb?.vision,
        domains: orb?.domains ?? s.profile.domains,
        holding: orb?.holding ?? s.profile.holding,
      },
    }));
    router.replace('/');
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: colors.parch }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={[styles.top, { paddingTop: insets.top + 16 }]}>
        <Orb size={32} thinking={thinking} />
        <Text style={styles.brand}>
          Orb<Text style={{ color: colors.terra, fontFamily: fonts.serifLightItalic }}>ou</Text>
        </Text>
        <View style={{ flex: 1 }} />
        {!orb ? (
          <Pressable onPress={() => enter(true)} hitSlop={12}>
            <Micro>Skip for now</Micro>
          </Pressable>
        ) : null}
      </View>

      <ScrollView ref={scroll} contentContainerStyle={styles.thread} keyboardShouldPersistTaps="handled">
        {chat.map((t, i) =>
          t.role === 'assistant' ? (
            <View key={i} style={styles.guardianRow}>
              <View style={{ marginTop: 4 }}>
                <Orb size={20} />
              </View>
              <Serif italic size={19} style={{ flex: 1, lineHeight: 28 }}>
                {t.content}
              </Serif>
            </View>
          ) : (
            <View key={i} style={styles.userBubble}>
              <Text style={styles.userText}>{t.content}</Text>
            </View>
          ),
        )}

        {thinking ? (
          <View style={[styles.guardianRow, { alignItems: 'center' }]}>
            <Orb size={24} thinking />
            <Micro>{orb || asking ? 'Organizing' : 'Listening'}</Micro>
          </View>
        ) : null}

        {asking && !orb && !thinking ? (
          <View style={{ gap: 10, marginTop: 8 }}>
            <Button label="Organize my orb" onPress={organize} />
            <Button label="Not yet — keep talking" kind="secondary" onPress={() => setDeclined(true)} />
          </View>
        ) : null}

        {orb ? (
          <Card style={{ marginTop: 12, gap: 14 }}>
            <Micro color={colors.gold}>Your orb</Micro>
            <Serif italic size={18} color={colors.inkM}>
              {orb.message}
            </Serif>
            <View>
              <Micro style={{ marginBottom: 8 }}>Who you’re becoming</Micro>
              <Field value={vision} onChangeText={setVision} multiline placeholder="I am someone who…" />
            </View>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
              {orb.domains.map((d) => (
                <Tag key={d} label={domainLabel[d as Domain] ?? d} color={domainColor[d as Domain] ?? colors.stone} />
              ))}
            </View>
            {orb.holding.length ? (
              <View style={{ gap: 6 }}>
                <Micro>I’ll hold</Micro>
                {orb.holding.map((h, i) => (
                  <Body key={i}>— {h}</Body>
                ))}
              </View>
            ) : null}
            <Button label="Enter your orb" onPress={() => enter()} />
          </Card>
        ) : null}
        {offline && !orb ? (
          <Micro style={{ textAlign: 'center', marginTop: 16 }}>Quiet mode — the full guardian wakes once the chat API is connected</Micro>
        ) : null}
      </ScrollView>

      {!orb ? (
        <View style={[styles.composer, { paddingBottom: insets.bottom + 12 }]}>
          <Field
            value={draft}
            onChangeText={setDraft}
            placeholder="Say whatever’s there…"
            style={styles.input}
            multiline
            onKeyPress={(e) => {
              // Enter sends on web; Shift+Enter keeps a newline.
              const ne = e.nativeEvent as { key: string; shiftKey?: boolean };
              if (Platform.OS === 'web' && ne.key === 'Enter' && !ne.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
          />
          <Pressable onPress={send} style={[styles.send, (!draft.trim() || thinking) && { opacity: 0.4 }]} accessibilityLabel="Send">
            <SendIcon color={colors.parch} />
          </Pressable>
        </View>
      ) : null}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  top: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 20, paddingBottom: 12, width: '100%', maxWidth: 640, alignSelf: 'center' },
  brand: { fontFamily: fonts.serifLight, fontSize: 26, color: colors.ink, letterSpacing: -0.5 },
  thread: { padding: 20, gap: 18, width: '100%', maxWidth: 640, alignSelf: 'center', paddingBottom: 32 },
  guardianRow: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  userBubble: {
    alignSelf: 'flex-end',
    maxWidth: '85%',
    backgroundColor: colors.surfaceS,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.card,
    borderBottomRightRadius: 4,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  userText: { fontFamily: fonts.sansLight, fontSize: 14, color: colors.ink, lineHeight: 21 },
  composer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 10,
    paddingHorizontal: 16,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    width: '100%',
    maxWidth: 640,
    alignSelf: 'center',
  },
  input: { flex: 1, minHeight: 48, maxHeight: 140, paddingVertical: 12, fontSize: 17 },
  send: { width: 48, height: 48, borderRadius: 24, backgroundColor: colors.terra, alignItems: 'center', justifyContent: 'center' },
});
