--
-- PostgreSQL database dump
--

\restrict 0oEOmcRIbrRi4Pc2OzjO4ZE7ZTDP2wQdbFAezo1lgOtCFGlOElgg3l3JAKyS4t1

-- Dumped from database version 16.10 (Debian 16.10-1.pgdg13+1)
-- Dumped by pg_dump version 16.10 (Debian 16.10-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: set_updated_at(); Type: FUNCTION; Schema: public; Owner: jensen
--

CREATE FUNCTION public.set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END $$;


ALTER FUNCTION public.set_updated_at() OWNER TO jensen;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: actions; Type: TABLE; Schema: public; Owner: jensen
--

CREATE TABLE public.actions (
    id integer NOT NULL,
    name text NOT NULL,
    kind text NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.actions OWNER TO jensen;

--
-- Name: actions_id_seq; Type: SEQUENCE; Schema: public; Owner: jensen
--

CREATE SEQUENCE public.actions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.actions_id_seq OWNER TO jensen;

--
-- Name: actions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jensen
--

ALTER SEQUENCE public.actions_id_seq OWNED BY public.actions.id;


--
-- Name: agent; Type: TABLE; Schema: public; Owner: jensen
--

CREATE TABLE public.agent (
    id integer NOT NULL,
    name character varying NOT NULL,
    description character varying,
    enabled boolean NOT NULL
);


ALTER TABLE public.agent OWNER TO jensen;

--
-- Name: agent_id_seq; Type: SEQUENCE; Schema: public; Owner: jensen
--

CREATE SEQUENCE public.agent_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.agent_id_seq OWNER TO jensen;

--
-- Name: agent_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jensen
--

ALTER SEQUENCE public.agent_id_seq OWNED BY public.agent.id;


--
-- Name: agents; Type: TABLE; Schema: public; Owner: jensen
--

CREATE TABLE public.agents (
    id integer NOT NULL,
    name character varying NOT NULL,
    description character varying,
    enabled boolean NOT NULL,
    tags json NOT NULL,
    routing_rules json NOT NULL
);


ALTER TABLE public.agents OWNER TO jensen;

--
-- Name: agents_id_seq; Type: SEQUENCE; Schema: public; Owner: jensen
--

CREATE SEQUENCE public.agents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.agents_id_seq OWNER TO jensen;

--
-- Name: agents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jensen
--

ALTER SEQUENCE public.agents_id_seq OWNED BY public.agents.id;


--
-- Name: audits; Type: TABLE; Schema: public; Owner: jensen
--

CREATE TABLE public.audits (
    id integer NOT NULL,
    event text NOT NULL,
    detail jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.audits OWNER TO jensen;

--
-- Name: audits_id_seq; Type: SEQUENCE; Schema: public; Owner: jensen
--

CREATE SEQUENCE public.audits_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audits_id_seq OWNER TO jensen;

--
-- Name: audits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jensen
--

ALTER SEQUENCE public.audits_id_seq OWNED BY public.audits.id;


--
-- Name: conversation; Type: TABLE; Schema: public; Owner: jensen
--

CREATE TABLE public.conversation (
    id integer NOT NULL
);


ALTER TABLE public.conversation OWNER TO jensen;

--
-- Name: conversation_id_seq; Type: SEQUENCE; Schema: public; Owner: jensen
--

CREATE SEQUENCE public.conversation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.conversation_id_seq OWNER TO jensen;

--
-- Name: conversation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jensen
--

ALTER SEQUENCE public.conversation_id_seq OWNED BY public.conversation.id;


--
-- Name: conversations; Type: TABLE; Schema: public; Owner: jensen
--

CREATE TABLE public.conversations (
    id integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    last_active_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.conversations OWNER TO jensen;

--
-- Name: conversations_id_seq; Type: SEQUENCE; Schema: public; Owner: jensen
--

CREATE SEQUENCE public.conversations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.conversations_id_seq OWNER TO jensen;

--
-- Name: conversations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jensen
--

ALTER SEQUENCE public.conversations_id_seq OWNED BY public.conversations.id;


--
-- Name: jobs; Type: TABLE; Schema: public; Owner: jensen
--

CREATE TABLE public.jobs (
    id integer NOT NULL,
    action_id integer,
    status text DEFAULT 'queued'::text NOT NULL,
    input jsonb DEFAULT '{}'::jsonb NOT NULL,
    result jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.jobs OWNER TO jensen;

--
-- Name: jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: jensen
--

CREATE SEQUENCE public.jobs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.jobs_id_seq OWNER TO jensen;

--
-- Name: jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jensen
--

ALTER SEQUENCE public.jobs_id_seq OWNED BY public.jobs.id;


--
-- Name: message; Type: TABLE; Schema: public; Owner: jensen
--

CREATE TABLE public.message (
    id integer NOT NULL,
    conversation_id integer NOT NULL,
    role character varying NOT NULL,
    content character varying NOT NULL
);


ALTER TABLE public.message OWNER TO jensen;

--
-- Name: message_id_seq; Type: SEQUENCE; Schema: public; Owner: jensen
--

CREATE SEQUENCE public.message_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.message_id_seq OWNER TO jensen;

--
-- Name: message_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jensen
--

ALTER SEQUENCE public.message_id_seq OWNED BY public.message.id;


--
-- Name: messages; Type: TABLE; Schema: public; Owner: jensen
--

CREATE TABLE public.messages (
    id integer NOT NULL,
    conversation_id integer NOT NULL,
    role character varying NOT NULL,
    content character varying NOT NULL,
    ts timestamp without time zone DEFAULT now() NOT NULL,
    agent_id integer
);


ALTER TABLE public.messages OWNER TO jensen;

--
-- Name: messages_id_seq; Type: SEQUENCE; Schema: public; Owner: jensen
--

CREATE SEQUENCE public.messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.messages_id_seq OWNER TO jensen;

--
-- Name: messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jensen
--

ALTER SEQUENCE public.messages_id_seq OWNED BY public.messages.id;


--
-- Name: actions id; Type: DEFAULT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.actions ALTER COLUMN id SET DEFAULT nextval('public.actions_id_seq'::regclass);


--
-- Name: agent id; Type: DEFAULT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.agent ALTER COLUMN id SET DEFAULT nextval('public.agent_id_seq'::regclass);


--
-- Name: agents id; Type: DEFAULT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.agents ALTER COLUMN id SET DEFAULT nextval('public.agents_id_seq'::regclass);


--
-- Name: audits id; Type: DEFAULT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.audits ALTER COLUMN id SET DEFAULT nextval('public.audits_id_seq'::regclass);


--
-- Name: conversation id; Type: DEFAULT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.conversation ALTER COLUMN id SET DEFAULT nextval('public.conversation_id_seq'::regclass);


--
-- Name: conversations id; Type: DEFAULT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.conversations ALTER COLUMN id SET DEFAULT nextval('public.conversations_id_seq'::regclass);


--
-- Name: jobs id; Type: DEFAULT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.jobs ALTER COLUMN id SET DEFAULT nextval('public.jobs_id_seq'::regclass);


--
-- Name: message id; Type: DEFAULT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.message ALTER COLUMN id SET DEFAULT nextval('public.message_id_seq'::regclass);


--
-- Name: messages id; Type: DEFAULT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.messages ALTER COLUMN id SET DEFAULT nextval('public.messages_id_seq'::regclass);


--
-- Data for Name: actions; Type: TABLE DATA; Schema: public; Owner: jensen
--

COPY public.actions (id, name, kind, config, enabled, created_at) FROM stdin;
1	ping_json_placeholder	http	{"url": "https://jsonplaceholder.typicode.com/todos/1", "method": "GET", "headers": {}, "timeout": 15}	t	2025-10-29 21:13:06.578678+00
\.


--
-- Data for Name: agent; Type: TABLE DATA; Schema: public; Owner: jensen
--

COPY public.agent (id, name, description, enabled) FROM stdin;
\.


--
-- Data for Name: agents; Type: TABLE DATA; Schema: public; Owner: jensen
--

COPY public.agents (id, name, description, enabled, tags, routing_rules) FROM stdin;
1	default	Fallback agent	t	["general"]	{}
2	sales	Sales Q&A	t	["pricing", "quote", "invoice"]	{}
3	support	Tech Support	t	["error", "bug", "issue"]	{}
\.


--
-- Data for Name: audits; Type: TABLE DATA; Schema: public; Owner: jensen
--

COPY public.audits (id, event, detail, created_at) FROM stdin;
1	job_queued	{"job_id": 2, "action_id": 1}	2025-10-29 21:14:24.024575+00
2	job_ok	{"job_id": 2, "result": {"body": {"id": 1, "title": "delectus aut autem", "userId": 1, "completed": false}, "status_code": 200}}	2025-10-29 21:14:25.617385+00
3	job_queued	{"job_id": 3, "action_id": 1}	2025-10-29 21:18:13.23641+00
4	job_ok	{"job_id": 3, "result": {"body": {"id": 1, "title": "delectus aut autem", "userId": 1, "completed": false}, "status_code": 200}}	2025-10-29 21:18:15.125909+00
5	job_queued	{"job_id": 4, "action_id": 1}	2025-10-29 22:03:50.979224+00
6	job_ok	{"job_id": 4, "result": {"body": {"id": 1, "title": "delectus aut autem", "userId": 1, "completed": false}, "status_code": 200}}	2025-10-29 22:03:52.04631+00
7	job_queued	{"job_id": 5, "action_id": 1}	2025-10-29 22:10:06.674925+00
8	job_ok	{"job_id": 5, "result": {"body": {"id": 1, "title": "delectus aut autem", "userId": 1, "completed": false}, "status_code": 200}}	2025-10-29 22:10:08.848965+00
\.


--
-- Data for Name: conversation; Type: TABLE DATA; Schema: public; Owner: jensen
--

COPY public.conversation (id) FROM stdin;
\.


--
-- Data for Name: conversations; Type: TABLE DATA; Schema: public; Owner: jensen
--

COPY public.conversations (id, created_at, last_active_at) FROM stdin;
1	2025-10-21 20:56:15.113708	2025-10-21 20:56:15.113714
2	2025-10-21 20:56:32.810139	2025-10-21 20:56:32.810145
3	2025-10-21 21:05:36.361386	2025-10-21 21:05:36.361392
4	2025-10-21 21:06:04.748657	2025-10-21 21:06:04.748663
5	2025-10-21 21:15:51.107505	2025-10-21 21:15:53.745385
6	2025-10-21 21:17:04.356776	2025-10-21 21:17:06.002719
7	2025-10-21 21:19:34.410492	2025-10-21 21:20:03.781714
8	2025-10-21 21:22:11.092551	2025-10-21 21:22:17.595872
9	2025-10-21 21:26:22.965132	2025-10-21 21:26:27.488511
10	2025-10-21 21:53:46.942507	2025-10-21 21:53:48.453552
\.


--
-- Data for Name: jobs; Type: TABLE DATA; Schema: public; Owner: jensen
--

COPY public.jobs (id, action_id, status, input, result, created_at, updated_at) FROM stdin;
2	1	ok	{"userId": 1}	{"body": {"id": 1, "title": "delectus aut autem", "userId": 1, "completed": false}, "status_code": 200}	2025-10-29 21:14:24.024575+00	2025-10-29 21:14:25.617385+00
3	1	ok	{"userId": 1}	{"body": {"id": 1, "title": "delectus aut autem", "userId": 1, "completed": false}, "status_code": 200}	2025-10-29 21:18:13.23641+00	2025-10-29 21:18:15.125909+00
4	1	ok	{"userId": 1}	{"body": {"id": 1, "title": "delectus aut autem", "userId": 1, "completed": false}, "status_code": 200}	2025-10-29 22:03:50.979224+00	2025-10-29 22:03:52.04631+00
5	1	ok	{"userId": 1}	{"body": {"id": 1, "title": "delectus aut autem", "userId": 1, "completed": false}, "status_code": 200}	2025-10-29 22:10:06.674925+00	2025-10-29 22:10:08.848965+00
\.


--
-- Data for Name: message; Type: TABLE DATA; Schema: public; Owner: jensen
--

COPY public.message (id, conversation_id, role, content) FROM stdin;
\.


--
-- Data for Name: messages; Type: TABLE DATA; Schema: public; Owner: jensen
--

COPY public.messages (id, conversation_id, role, content, ts, agent_id) FROM stdin;
1	3	user	Hello from Ali	2025-10-21 21:05:47.369125	\N
2	4	user	Hello again over HTTPS	2025-10-21 21:06:04.950903	\N
3	5	user	Hello from Ali	2025-10-21 21:15:52.157997	\N
4	5	assistant	Hello, Ali! How can I assist you today?	2025-10-21 21:15:53.745174	\N
5	6	user	Hello from Ali over HTTPS	2025-10-21 21:17:04.527544	\N
6	6	assistant	Hello, Ali! How can I assist you today?	2025-10-21 21:17:06.002518	\N
7	7	user	Can I get pricing for the pro plan?	2025-10-21 21:19:38.262557	2
8	7	assistant	I don't have real-time pricing information, but you can typically find the most accurate and up-to-date pricing for the pro plan on the official website of the service you're interested in. If you provide the name of the service, I might be able to guide you on where to look!	2025-10-21 21:19:41.144696	2
9	7	user	I hit an error when logging in	2025-10-21 21:19:41.319332	3
10	7	assistant	I'm sorry to hear you're having trouble logging in. Here are some general steps you can take to troubleshoot the issue:\n\n1. **Check Credentials**: Ensure that you're entering the correct username and password. Pay attention to case sensitivity.\n\n2. **Reset Password**: If you're unsure about your password, use the "Forgot Password?" link to reset it.\n\n3. **Clear Cache and Cookies**: Sometimes, clearing your browser's cache and cookies can resolve login issues.\n\n4. **Try a Different Browser or Device**: If possible, try logging in from a different browser or device to see if the issue persists.\n\n5. **Disable Extensions**: Browser extensions can sometimes interfere with login processes. Try disabling them temporarily.\n\n6. **Check Service Status**: Sometimes, the service may be experiencing outages. Check their official website or social media for any announcements.\n\n7. **Contact Support**: If none of the above steps work, reach out to the service's customer support for assistance.\n\nIf you provide more details about the specific service, I might be able to offer more tailored advice!	2025-10-21 21:19:44.692319	3
11	7	user	Answer as support please	2025-10-21 21:19:57.274597	2
12	7	assistant	Certainly! Here’s a response you might receive from customer support:\n\n---\n\n**Subject: Login Issue Assistance**\n\nDear [User's Name],\n\nThank you for reaching out to us regarding the login error you are experiencing. We’re here to help!\n\nPlease follow these troubleshooting steps to resolve the issue:\n\n1. **Verify Your Credentials**: Ensure that you are entering the correct username and password. Please note that passwords are case-sensitive.\n\n2. **Reset Your Password**: If you’re unsure about your password, you can reset it by clicking on the "Forgot Password?" link on the login page. Follow the instructions sent to your registered email.\n\n3. **Clear Cache and Cookies**: Sometimes, browser cache and cookies can cause login issues. Please try clearing them and then attempt to log in again.\n\n4. **Try a Different Browser or Device**: If possible, please try logging in from a different web browser or device to see if the issue persists.\n\n5. **Disable Browser Extensions**: Certain browser extensions can interfere with the login process. Try disabling them temporarily and see if that resolves the issue.\n\n6. **Check Service Status**: Occasionally, our service may experience outages. You can check our [status page/website/social media] for any updates.\n\nIf you have tried all of the above and are still unable to log in, please provide us with any error messages you are receiving, and we will investigate further.\n\nThank you for your patience, and we look forward to resolving this issue for you.\n\nBest regards,\n\n[Your Name]  \nCustomer Support Team  \n[Company Name]  \n[Contact Information]\n\n--- \n\nFeel free to customize any part of this response as needed!	2025-10-21 21:20:03.781521	2
13	8	user	pricing for team plan?	2025-10-21 21:22:11.203663	2
14	8	assistant	Could you please specify which service or platform you are inquiring about for the team plan pricing? Different services have different pricing structures.	2025-10-21 21:22:12.254855	2
15	8	user	login error on mobile	2025-10-21 21:22:12.437154	3
16	8	assistant	If you're experiencing a login error on your mobile device, here are some steps you can try to resolve the issue:\n\n1. **Check Credentials**: Ensure that you are entering the correct username and password. Pay attention to case sensitivity.\n\n2. **Reset Password**: If you’ve forgotten your password, use the "Forgot Password?" link to reset it.\n\n3. **Update the App**: Make sure that the app is updated to the latest version available in your app store.\n\n4. **Clear Cache**: If you're using a web browser, try clearing the cache and cookies. For apps, you can clear the app cache in your device settings.\n\n5. **Check Internet Connection**: Ensure that you have a stable internet connection, either through Wi-Fi or mobile data.\n\n6. **Reinstall the App**: If the problem persists, try uninstalling and then reinstalling the app.\n\n7. **Check for Service Outages**: Sometimes, the service may be down. Check the service's official website or social media for any announcements.\n\n8. **Contact Support**: If none of the above steps work, reach out to the customer support team of the service for further assistance.\n\nIf you provide more details about the specific app or service, I can offer more tailored advice.	2025-10-21 21:22:17.595687	3
17	9	user	pricing for team plan?	2025-10-21 21:26:23.094219	2
18	9	assistant	I would need to know which service or product you are referring to in order to provide accurate pricing for a team plan. Could you please specify?	2025-10-21 21:26:24.121745	2
19	9	user	login error on mobile	2025-10-21 21:26:24.23757	3
20	9	assistant	If you're experiencing a login error on mobile, here are some steps you can try to resolve the issue:\n\n1. **Check Credentials**: Ensure that you are entering the correct username and password. Pay attention to case sensitivity.\n\n2. **Reset Password**: If you're unsure about your password, try resetting it through the "Forgot Password?" link.\n\n3. **Update App**: Make sure that the app is updated to the latest version available in your app store.\n\n4. **Clear Cache**: If you're using a mobile browser, try clearing the cache and cookies. If you're using an app, you may need to clear the app cache in your device settings.\n\n5. **Reinstall the App**: Uninstall and then reinstall the app to see if that resolves the issue.\n\n6. **Check Internet Connection**: Ensure that you have a stable internet connection.\n\n7. **Disable VPN**: If you are using a VPN, try disabling it, as it may interfere with the login process.\n\n8. **Contact Support**: If none of the above steps work, consider reaching out to the support team of the service for further assistance.\n\nIf you provide more details about the specific app or service, I might be able to offer more tailored advice.	2025-10-21 21:26:27.48833	3
21	10	user	Hello, what can you do?	2025-10-21 21:53:47.056413	1
22	10	assistant	Hello! I can assist you with a variety of tasks, including answering questions, providing information, helping with problem-solving, offering writing and editing support, and giving recommendations on various topics. How can I help you today?	2025-10-21 21:53:48.453335	1
\.


--
-- Name: actions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jensen
--

SELECT pg_catalog.setval('public.actions_id_seq', 1, true);


--
-- Name: agent_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jensen
--

SELECT pg_catalog.setval('public.agent_id_seq', 1, false);


--
-- Name: agents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jensen
--

SELECT pg_catalog.setval('public.agents_id_seq', 3, true);


--
-- Name: audits_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jensen
--

SELECT pg_catalog.setval('public.audits_id_seq', 8, true);


--
-- Name: conversation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jensen
--

SELECT pg_catalog.setval('public.conversation_id_seq', 1, false);


--
-- Name: conversations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jensen
--

SELECT pg_catalog.setval('public.conversations_id_seq', 10, true);


--
-- Name: jobs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jensen
--

SELECT pg_catalog.setval('public.jobs_id_seq', 5, true);


--
-- Name: message_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jensen
--

SELECT pg_catalog.setval('public.message_id_seq', 1, false);


--
-- Name: messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jensen
--

SELECT pg_catalog.setval('public.messages_id_seq', 22, true);


--
-- Name: actions actions_name_key; Type: CONSTRAINT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.actions
    ADD CONSTRAINT actions_name_key UNIQUE (name);


--
-- Name: actions actions_pkey; Type: CONSTRAINT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.actions
    ADD CONSTRAINT actions_pkey PRIMARY KEY (id);


--
-- Name: agent agent_pkey; Type: CONSTRAINT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.agent
    ADD CONSTRAINT agent_pkey PRIMARY KEY (id);


--
-- Name: agents agents_pkey; Type: CONSTRAINT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_pkey PRIMARY KEY (id);


--
-- Name: audits audits_pkey; Type: CONSTRAINT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.audits
    ADD CONSTRAINT audits_pkey PRIMARY KEY (id);


--
-- Name: conversation conversation_pkey; Type: CONSTRAINT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.conversation
    ADD CONSTRAINT conversation_pkey PRIMARY KEY (id);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: message message_pkey; Type: CONSTRAINT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.message
    ADD CONSTRAINT message_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: agents uq_agent_name; Type: CONSTRAINT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT uq_agent_name UNIQUE (name);


--
-- Name: idx_audits_created_at; Type: INDEX; Schema: public; Owner: jensen
--

CREATE INDEX idx_audits_created_at ON public.audits USING btree (created_at DESC);


--
-- Name: idx_audits_event; Type: INDEX; Schema: public; Owner: jensen
--

CREATE INDEX idx_audits_event ON public.audits USING btree (event);


--
-- Name: ix_agents_enabled; Type: INDEX; Schema: public; Owner: jensen
--

CREATE INDEX ix_agents_enabled ON public.agents USING btree (enabled);


--
-- Name: ix_agents_name; Type: INDEX; Schema: public; Owner: jensen
--

CREATE INDEX ix_agents_name ON public.agents USING btree (name);


--
-- Name: ix_message_conversation_id; Type: INDEX; Schema: public; Owner: jensen
--

CREATE INDEX ix_message_conversation_id ON public.message USING btree (conversation_id);


--
-- Name: ix_messages_conversation_id; Type: INDEX; Schema: public; Owner: jensen
--

CREATE INDEX ix_messages_conversation_id ON public.messages USING btree (conversation_id);


--
-- Name: jobs jobs_set_updated_at; Type: TRIGGER; Schema: public; Owner: jensen
--

CREATE TRIGGER jobs_set_updated_at BEFORE UPDATE ON public.jobs FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: jobs jobs_action_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jensen
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_action_id_fkey FOREIGN KEY (action_id) REFERENCES public.actions(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict 0oEOmcRIbrRi4Pc2OzjO4ZE7ZTDP2wQdbFAezo1lgOtCFGlOElgg3l3JAKyS4t1

