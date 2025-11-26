--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.4

-- Started on 2025-11-22 00:18:42

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 250 (class 1255 OID 34576)
-- Name: generate_pwd_unique_id(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.generate_pwd_unique_id() RETURNS character varying
    LANGUAGE plpgsql
    AS $$
DECLARE
    current_year INTEGER;
    next_number INTEGER;
    new_id VARCHAR(20);
BEGIN
    -- Get current year
    current_year := EXTRACT(YEAR FROM CURRENT_DATE);
    
    -- Find the highest number for current year
    SELECT COALESCE(
        MAX(CAST(SPLIT_PART(unique_pwd_id, '-', 2) AS INTEGER)), 
        0
    ) + 1
    INTO next_number
    FROM pwd_profiles
    WHERE unique_pwd_id LIKE current_year || '-%';
    
    -- Format: YYYY-####
    new_id := current_year || '-' || LPAD(next_number::TEXT, 4, '0');
    
    RETURN new_id;
END;
$$;


ALTER FUNCTION public.generate_pwd_unique_id() OWNER TO postgres;

--
-- TOC entry 5045 (class 0 OID 0)
-- Dependencies: 250
-- Name: FUNCTION generate_pwd_unique_id(); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.generate_pwd_unique_id() IS 'Generates next unique PWD ID in format YYYY-####';


--
-- TOC entry 249 (class 1255 OID 34573)
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 220 (class 1259 OID 34474)
-- Name: audit_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_log (
    id integer NOT NULL,
    action_type character varying(50) NOT NULL,
    description text NOT NULL,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ip_address character varying(45),
    user_id integer,
    target_user_id integer,
    target_pwd_id integer,
    CONSTRAINT chk_action_type CHECK (((action_type)::text = ANY ((ARRAY['user_registered'::character varying, 'user_verified'::character varying, 'user_deactivated'::character varying, 'user_reactivated'::character varying, 'pwd_created'::character varying, 'pwd_updated'::character varying, 'pwd_archived'::character varying, 'pwd_reactivated'::character varying, 'password_changed'::character varying, 'password_reset'::character varying, 'login'::character varying, 'logout'::character varying, 'profile_updated'::character varying, 'document_uploaded'::character varying, 'document_deleted'::character varying])::text[])))
);


ALTER TABLE public.audit_log OWNER TO postgres;

--
-- TOC entry 5046 (class 0 OID 0)
-- Dependencies: 220
-- Name: TABLE audit_log; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.audit_log IS 'System activity audit trail';


--
-- TOC entry 5047 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN audit_log.user_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.audit_log.user_id IS 'User who performed the action';


--
-- TOC entry 5048 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN audit_log.target_user_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.audit_log.target_user_id IS 'User affected by the action';


--
-- TOC entry 5049 (class 0 OID 0)
-- Dependencies: 220
-- Name: COLUMN audit_log.target_pwd_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.audit_log.target_pwd_id IS 'PWD profile affected by the action';


--
-- TOC entry 219 (class 1259 OID 34473)
-- Name: audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_log_id_seq OWNER TO postgres;

--
-- TOC entry 5050 (class 0 OID 0)
-- Dependencies: 219
-- Name: audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.audit_log_id_seq OWNED BY public.audit_log.id;


--
-- TOC entry 237 (class 1259 OID 34624)
-- Name: auth_group; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE public.auth_group OWNER TO postgres;

--
-- TOC entry 236 (class 1259 OID 34623)
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_group ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 239 (class 1259 OID 34632)
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_group_permissions (
    id bigint NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_group_permissions OWNER TO postgres;

--
-- TOC entry 238 (class 1259 OID 34631)
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_group_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 235 (class 1259 OID 34618)
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE public.auth_permission OWNER TO postgres;

--
-- TOC entry 234 (class 1259 OID 34617)
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_permission ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 241 (class 1259 OID 34638)
-- Name: auth_user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_user (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(150) NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL
);


ALTER TABLE public.auth_user OWNER TO postgres;

--
-- TOC entry 243 (class 1259 OID 34646)
-- Name: auth_user_groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_user_groups (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.auth_user_groups OWNER TO postgres;

--
-- TOC entry 242 (class 1259 OID 34645)
-- Name: auth_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_user_groups ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 240 (class 1259 OID 34637)
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_user ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 245 (class 1259 OID 34652)
-- Name: auth_user_user_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_user_user_permissions (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_user_user_permissions OWNER TO postgres;

--
-- TOC entry 244 (class 1259 OID 34651)
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.auth_user_user_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 247 (class 1259 OID 34710)
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id integer NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


ALTER TABLE public.django_admin_log OWNER TO postgres;

--
-- TOC entry 246 (class 1259 OID 34709)
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.django_admin_log ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_admin_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 233 (class 1259 OID 34610)
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE public.django_content_type OWNER TO postgres;

--
-- TOC entry 232 (class 1259 OID 34609)
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.django_content_type ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 231 (class 1259 OID 34602)
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_migrations (
    id bigint NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE public.django_migrations OWNER TO postgres;

--
-- TOC entry 230 (class 1259 OID 34601)
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.django_migrations ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 248 (class 1259 OID 34738)
-- Name: django_session; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE public.django_session OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 34544)
-- Name: pwd_documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pwd_documents (
    id integer NOT NULL,
    pwd_profile_id integer NOT NULL,
    uploaded_by integer,
    file_path character varying(255) NOT NULL,
    file_name character varying(255) NOT NULL,
    file_type character varying(10) NOT NULL,
    file_size integer NOT NULL,
    uploaded_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_file_size CHECK (((file_size > 0) AND (file_size <= 5242880))),
    CONSTRAINT chk_file_type CHECK (((file_type)::text = ANY ((ARRAY['pdf'::character varying, 'PDF'::character varying])::text[])))
);


ALTER TABLE public.pwd_documents OWNER TO postgres;

--
-- TOC entry 5051 (class 0 OID 0)
-- Dependencies: 224
-- Name: TABLE pwd_documents; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.pwd_documents IS 'Supporting documents (PDFs) for PWD profiles';


--
-- TOC entry 5052 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN pwd_documents.uploaded_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.pwd_documents.uploaded_by IS 'User who uploaded the document';


--
-- TOC entry 5053 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN pwd_documents.file_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.pwd_documents.file_type IS 'File extension (PDF only)';


--
-- TOC entry 5054 (class 0 OID 0)
-- Dependencies: 224
-- Name: COLUMN pwd_documents.file_size; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.pwd_documents.file_size IS 'File size in bytes (max 5MB)';


--
-- TOC entry 223 (class 1259 OID 34543)
-- Name: pwd_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.pwd_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pwd_documents_id_seq OWNER TO postgres;

--
-- TOC entry 5055 (class 0 OID 0)
-- Dependencies: 223
-- Name: pwd_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.pwd_documents_id_seq OWNED BY public.pwd_documents.id;


--
-- TOC entry 222 (class 1259 OID 34500)
-- Name: pwd_profile; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pwd_profile (
    id integer NOT NULL,
    unique_id character varying(20) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by integer NOT NULL,
    updated_by integer,
    first_name character varying(100) NOT NULL,
    middle_name character varying(100),
    last_name character varying(100) NOT NULL,
    suffix character varying(10),
    birthdate date NOT NULL,
    sex character(1) NOT NULL,
    religion character varying(100) NOT NULL,
    barangay character varying(100) NOT NULL,
    address text NOT NULL,
    contact_number character varying(20) NOT NULL,
    nationality character varying(50) DEFAULT 'Filipino'::character varying NOT NULL,
    civil_status character varying(20) NOT NULL,
    photo_path character varying(255),
    living_situation character varying(100) NOT NULL,
    guardian_name character varying(200) NOT NULL,
    guardian_contact character varying(20) NOT NULL,
    household_income numeric(10,2),
    household_size integer,
    housing_type character varying(50),
    educational_attainment character varying(50) NOT NULL,
    employment_status character varying(20) NOT NULL,
    occupation character varying(100) NOT NULL,
    type_of_employment character varying(50),
    disability_type character varying(100) NOT NULL,
    cause_of_disability character varying(200) NOT NULL,
    degree_of_disability character varying(20) NOT NULL,
    date_diagnosed date,
    assistive_devices character varying(200),
    medication text,
    allergies text,
    emergency_contact_name character varying(200) NOT NULL,
    emergency_contact_number character varying(20) NOT NULL,
    emergency_contact_address text NOT NULL,
    philhealth_number character varying(20),
    sss_gsis_number character varying(20),
    skills_hobbies text,
    organization_membership text,
    government_health_benefits text,
    remarks text,
    fingerprint_data bytea,
    CONSTRAINT chk_pwd_birthdate CHECK ((birthdate <= CURRENT_DATE)),
    CONSTRAINT chk_pwd_civil_status CHECK (((civil_status)::text = ANY ((ARRAY['Single'::character varying, 'Married'::character varying, 'Widowed'::character varying, 'Divorced'::character varying, 'Separated'::character varying])::text[]))),
    CONSTRAINT chk_pwd_degree CHECK (((degree_of_disability)::text = ANY ((ARRAY['Low'::character varying, 'Moderate'::character varying, 'High'::character varying])::text[]))),
    CONSTRAINT chk_pwd_employment CHECK (((employment_status)::text = ANY ((ARRAY['Employed'::character varying, 'Unemployed'::character varying, 'Self-Employed'::character varying, 'Student'::character varying, 'Retired'::character varying])::text[]))),
    CONSTRAINT chk_pwd_sex CHECK ((sex = ANY (ARRAY['M'::bpchar, 'F'::bpchar]))),
    CONSTRAINT chk_unique_pwd_id_format CHECK (((unique_id)::text ~ '^\d{4}-\d{4}$'::text))
);


ALTER TABLE public.pwd_profile OWNER TO postgres;

--
-- TOC entry 5056 (class 0 OID 0)
-- Dependencies: 222
-- Name: TABLE pwd_profile; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.pwd_profile IS 'PWD (Persons with Disabilities) profile records';


--
-- TOC entry 5057 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN pwd_profile.unique_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.pwd_profile.unique_id IS 'Year-based unique ID (e.g., 2025-0001)';


--
-- TOC entry 5058 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN pwd_profile.is_active; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.pwd_profile.is_active IS 'FALSE = Deceased/Archived';


--
-- TOC entry 5059 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN pwd_profile.created_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.pwd_profile.created_by IS 'User who registered this PWD';


--
-- TOC entry 5060 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN pwd_profile.updated_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.pwd_profile.updated_by IS 'User who last updated this PWD';


--
-- TOC entry 5061 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN pwd_profile.degree_of_disability; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.pwd_profile.degree_of_disability IS 'Low, Moderate, or High';


--
-- TOC entry 221 (class 1259 OID 34499)
-- Name: pwd_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.pwd_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pwd_profiles_id_seq OWNER TO postgres;

--
-- TOC entry 5062 (class 0 OID 0)
-- Dependencies: 221
-- Name: pwd_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.pwd_profiles_id_seq OWNED BY public.pwd_profile.id;


--
-- TOC entry 218 (class 1259 OID 34441)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(150) NOT NULL,
    password character varying(128) NOT NULL,
    role character varying(20) DEFAULT 'basic_user'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_verified boolean DEFAULT false NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    verified_at timestamp without time zone,
    verified_by integer,
    security_question character varying(255) NOT NULL,
    security_answer character varying(128) NOT NULL,
    first_name character varying(100) NOT NULL,
    middle_name character varying(100),
    last_name character varying(100) NOT NULL,
    suffix character varying(10),
    birthdate date NOT NULL,
    sex character(1) NOT NULL,
    religion character varying(100) NOT NULL,
    home_address text NOT NULL,
    contact_number character varying(20) NOT NULL,
    nationality character varying(50) DEFAULT 'Filipino'::character varying NOT NULL,
    civil_status character varying(20) NOT NULL,
    educational_attainment character varying(50) NOT NULL,
    employment_status character varying(20) NOT NULL,
    occupation character varying(100) NOT NULL,
    emergency_contact_name character varying(200) NOT NULL,
    emergency_contact_number character varying(20) NOT NULL,
    emergency_contact_address text NOT NULL,
    valid_id_path character varying(255) NOT NULL,
    CONSTRAINT chk_birthdate CHECK ((birthdate <= (CURRENT_DATE - '18 years'::interval))),
    CONSTRAINT chk_civil_status CHECK (((civil_status)::text = ANY ((ARRAY['Single'::character varying, 'Married'::character varying, 'Widowed'::character varying, 'Divorced'::character varying, 'Separated'::character varying])::text[]))),
    CONSTRAINT chk_employment_status CHECK (((employment_status)::text = ANY ((ARRAY['Employed'::character varying, 'Unemployed'::character varying, 'Self-Employed'::character varying, 'Student'::character varying, 'Retired'::character varying])::text[]))),
    CONSTRAINT chk_role CHECK (((role)::text = ANY ((ARRAY['admin'::character varying, 'basic_user'::character varying])::text[]))),
    CONSTRAINT chk_sex CHECK ((sex = ANY (ARRAY['M'::bpchar, 'F'::bpchar])))
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 5063 (class 0 OID 0)
-- Dependencies: 218
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.users IS 'User accounts for admin and basic users';


--
-- TOC entry 5064 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN users.password; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.password IS 'Hashed password using Django PBKDF2';


--
-- TOC entry 5065 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN users.is_verified; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.is_verified IS 'Whether admin has manually verified this user';


--
-- TOC entry 5066 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN users.verified_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.verified_by IS 'Admin user ID who verified this account';


--
-- TOC entry 5067 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN users.security_answer; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.security_answer IS 'Hashed security answer';


--
-- TOC entry 217 (class 1259 OID 34440)
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- TOC entry 5068 (class 0 OID 0)
-- Dependencies: 217
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- TOC entry 225 (class 1259 OID 34577)
-- Name: vw_active_pwd_profiles; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_active_pwd_profiles AS
 SELECT p.id,
    p.unique_id AS unique_pwd_id,
    p.first_name,
    p.middle_name,
    p.last_name,
    p.suffix,
    p.birthdate,
    EXTRACT(year FROM age((p.birthdate)::timestamp with time zone)) AS age,
    p.sex,
    p.barangay,
    p.degree_of_disability,
    p.employment_status,
    p.created_at,
    u.username AS created_by_username,
    (((u.first_name)::text || ' '::text) || (u.last_name)::text) AS created_by_name
   FROM (public.pwd_profile p
     JOIN public.users u ON ((p.created_by = u.id)))
  WHERE (p.is_active = true);


ALTER VIEW public.vw_active_pwd_profiles OWNER TO postgres;

--
-- TOC entry 5069 (class 0 OID 0)
-- Dependencies: 225
-- Name: VIEW vw_active_pwd_profiles; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.vw_active_pwd_profiles IS 'Active PWD profiles with creator information';


--
-- TOC entry 227 (class 1259 OID 34586)
-- Name: vw_dashboard_stats; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_dashboard_stats AS
 SELECT ( SELECT count(*) AS count
           FROM public.pwd_profile
          WHERE (pwd_profile.is_active = true)) AS total_active_pwd,
    ( SELECT count(*) AS count
           FROM public.pwd_profile
          WHERE (pwd_profile.is_active = false)) AS total_inactive_pwd,
    ( SELECT count(*) AS count
           FROM public.users
          WHERE (((users.role)::text = 'basic_user'::text) AND (users.is_active = true))) AS total_active_users,
    ( SELECT count(*) AS count
           FROM public.users
          WHERE (((users.role)::text = 'basic_user'::text) AND (users.is_verified = false))) AS unverified_users,
    ( SELECT count(*) AS count
           FROM public.pwd_profile
          WHERE ((pwd_profile.sex = 'M'::bpchar) AND (pwd_profile.is_active = true))) AS male_pwd,
    ( SELECT count(*) AS count
           FROM public.pwd_profile
          WHERE ((pwd_profile.sex = 'F'::bpchar) AND (pwd_profile.is_active = true))) AS female_pwd,
    ( SELECT count(*) AS count
           FROM public.pwd_profile
          WHERE (((pwd_profile.degree_of_disability)::text = 'Low'::text) AND (pwd_profile.is_active = true))) AS low_degree,
    ( SELECT count(*) AS count
           FROM public.pwd_profile
          WHERE (((pwd_profile.degree_of_disability)::text = 'Moderate'::text) AND (pwd_profile.is_active = true))) AS moderate_degree,
    ( SELECT count(*) AS count
           FROM public.pwd_profile
          WHERE (((pwd_profile.degree_of_disability)::text = 'High'::text) AND (pwd_profile.is_active = true))) AS high_degree,
    ( SELECT count(*) AS count
           FROM public.pwd_profile
          WHERE (((pwd_profile.employment_status)::text = 'Employed'::text) AND (pwd_profile.is_active = true))) AS employed_pwd,
    ( SELECT count(*) AS count
           FROM public.pwd_profile
          WHERE (((pwd_profile.employment_status)::text = 'Unemployed'::text) AND (pwd_profile.is_active = true))) AS unemployed_pwd,
    ( SELECT count(*) AS count
           FROM public.pwd_profile
          WHERE (((pwd_profile.employment_status)::text = 'Self-Employed'::text) AND (pwd_profile.is_active = true))) AS self_employed_pwd,
    ( SELECT count(*) AS count
           FROM public.pwd_profile
          WHERE (((pwd_profile.employment_status)::text = 'Student'::text) AND (pwd_profile.is_active = true))) AS student_pwd,
    ( SELECT count(*) AS count
           FROM public.pwd_profile
          WHERE (((pwd_profile.employment_status)::text = 'Retired'::text) AND (pwd_profile.is_active = true))) AS retired_pwd;


ALTER VIEW public.vw_dashboard_stats OWNER TO postgres;

--
-- TOC entry 5070 (class 0 OID 0)
-- Dependencies: 227
-- Name: VIEW vw_dashboard_stats; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.vw_dashboard_stats IS 'Pre-calculated statistics for admin dashboard';


--
-- TOC entry 228 (class 1259 OID 34591)
-- Name: vw_pwd_age_groups; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_pwd_age_groups AS
 SELECT
        CASE
            WHEN (EXTRACT(year FROM age((birthdate)::timestamp with time zone)) < (18)::numeric) THEN '1-17 years'::text
            WHEN ((EXTRACT(year FROM age((birthdate)::timestamp with time zone)) >= (18)::numeric) AND (EXTRACT(year FROM age((birthdate)::timestamp with time zone)) <= (30)::numeric)) THEN '18-30 years'::text
            WHEN ((EXTRACT(year FROM age((birthdate)::timestamp with time zone)) >= (31)::numeric) AND (EXTRACT(year FROM age((birthdate)::timestamp with time zone)) <= (59)::numeric)) THEN '31-59 years'::text
            ELSE '60+ years'::text
        END AS age_group,
    count(*) AS count
   FROM public.pwd_profile
  WHERE (is_active = true)
  GROUP BY
        CASE
            WHEN (EXTRACT(year FROM age((birthdate)::timestamp with time zone)) < (18)::numeric) THEN '1-17 years'::text
            WHEN ((EXTRACT(year FROM age((birthdate)::timestamp with time zone)) >= (18)::numeric) AND (EXTRACT(year FROM age((birthdate)::timestamp with time zone)) <= (30)::numeric)) THEN '18-30 years'::text
            WHEN ((EXTRACT(year FROM age((birthdate)::timestamp with time zone)) >= (31)::numeric) AND (EXTRACT(year FROM age((birthdate)::timestamp with time zone)) <= (59)::numeric)) THEN '31-59 years'::text
            ELSE '60+ years'::text
        END
  ORDER BY
        CASE
            WHEN (EXTRACT(year FROM age((birthdate)::timestamp with time zone)) < (18)::numeric) THEN '1-17 years'::text
            WHEN ((EXTRACT(year FROM age((birthdate)::timestamp with time zone)) >= (18)::numeric) AND (EXTRACT(year FROM age((birthdate)::timestamp with time zone)) <= (30)::numeric)) THEN '18-30 years'::text
            WHEN ((EXTRACT(year FROM age((birthdate)::timestamp with time zone)) >= (31)::numeric) AND (EXTRACT(year FROM age((birthdate)::timestamp with time zone)) <= (59)::numeric)) THEN '31-59 years'::text
            ELSE '60+ years'::text
        END;


ALTER VIEW public.vw_pwd_age_groups OWNER TO postgres;

--
-- TOC entry 5071 (class 0 OID 0)
-- Dependencies: 228
-- Name: VIEW vw_pwd_age_groups; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.vw_pwd_age_groups IS 'PWD profiles grouped by age ranges';


--
-- TOC entry 229 (class 1259 OID 34596)
-- Name: vw_recent_activities; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_recent_activities AS
 SELECT a.id,
    a.action_type,
    a.description,
    a."timestamp",
    u.username,
    (((u.first_name)::text || ' '::text) || (u.last_name)::text) AS user_full_name
   FROM (public.audit_log a
     LEFT JOIN public.users u ON ((a.user_id = u.id)))
  ORDER BY a."timestamp" DESC
 LIMIT 10;


ALTER VIEW public.vw_recent_activities OWNER TO postgres;

--
-- TOC entry 5072 (class 0 OID 0)
-- Dependencies: 229
-- Name: VIEW vw_recent_activities; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.vw_recent_activities IS 'Last 10 audit log entries for dashboard';


--
-- TOC entry 226 (class 1259 OID 34582)
-- Name: vw_unverified_users; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_unverified_users AS
 SELECT id,
    username,
    first_name,
    middle_name,
    last_name,
    contact_number,
    created_at,
    is_active
   FROM public.users
  WHERE ((is_verified = false) AND ((role)::text = 'basic_user'::text));


ALTER VIEW public.vw_unverified_users OWNER TO postgres;

--
-- TOC entry 5073 (class 0 OID 0)
-- Dependencies: 226
-- Name: VIEW vw_unverified_users; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON VIEW public.vw_unverified_users IS 'Users awaiting admin verification';


--
-- TOC entry 4734 (class 2604 OID 34477)
-- Name: audit_log id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_log ALTER COLUMN id SET DEFAULT nextval('public.audit_log_id_seq'::regclass);


--
-- TOC entry 4741 (class 2604 OID 34547)
-- Name: pwd_documents id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pwd_documents ALTER COLUMN id SET DEFAULT nextval('public.pwd_documents_id_seq'::regclass);


--
-- TOC entry 4736 (class 2604 OID 34503)
-- Name: pwd_profile id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pwd_profile ALTER COLUMN id SET DEFAULT nextval('public.pwd_profiles_id_seq'::regclass);


--
-- TOC entry 4727 (class 2604 OID 34444)
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- TOC entry 5016 (class 0 OID 34474)
-- Dependencies: 220
-- Data for Name: audit_log; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.audit_log (id, action_type, description, "timestamp", ip_address, user_id, target_user_id, target_pwd_id) FROM stdin;
1	user_registered	System admin account created via management command	2025-11-20 15:44:15.061775	\N	1	\N	\N
2	login	User admin logged in	2025-11-20 16:39:16.112537	127.0.0.1	1	\N	\N
3	logout	User admin logged out	2025-11-20 16:40:11.419555	127.0.0.1	1	\N	\N
4	login	User admin logged in	2025-11-20 16:40:19.949917	127.0.0.1	1	\N	\N
5	logout	User admin logged out	2025-11-20 17:08:14.78795	127.0.0.1	1	\N	\N
6	user_registered	New user registered: meow	2025-11-20 17:14:14.552244	127.0.0.1	2	\N	\N
7	login	User meow logged in	2025-11-20 17:14:39.890212	127.0.0.1	2	\N	\N
8	logout	User meow logged out	2025-11-21 06:18:50.59717	127.0.0.1	2	\N	\N
9	login	User admin logged in	2025-11-21 06:19:18.972429	127.0.0.1	1	\N	\N
10	user_verified	Admin admin verified user meow	2025-11-21 06:19:36.491501	127.0.0.1	1	2	\N
11	user_deactivated	Admin admin deactivated user meow	2025-11-21 06:20:12.626436	127.0.0.1	1	2	\N
12	logout	User admin logged out	2025-11-21 06:20:22.896673	127.0.0.1	1	\N	\N
13	login	User admin logged in	2025-11-21 06:41:38.410571	127.0.0.1	1	\N	\N
14	logout	User admin logged out	2025-11-21 06:42:09.342126	127.0.0.1	1	\N	\N
15	user_registered	New user registered: qwe	2025-11-21 07:14:15.774776	127.0.0.1	3	\N	\N
16	password_reset	User qwe reset their password via security question	2025-11-21 07:14:48.427219	127.0.0.1	3	\N	\N
17	login	User qwe logged in	2025-11-21 07:15:17.253319	127.0.0.1	3	\N	\N
18	profile_updated	User qwe updated their profile	2025-11-21 07:15:50.577922	127.0.0.1	3	\N	\N
19	logout	User qwe logged out	2025-11-21 07:16:06.83886	127.0.0.1	3	\N	\N
20	login	User admin logged in	2025-11-21 07:16:34.779689	127.0.0.1	1	\N	\N
21	user_verified	Admin admin verified user qwe	2025-11-21 07:17:20.818736	127.0.0.1	1	3	\N
24	password_reset	Admin admin reset password for user qwe	2025-11-21 07:22:50.179527	127.0.0.1	1	3	\N
25	logout	User admin logged out	2025-11-21 07:28:57.352124	127.0.0.1	1	\N	\N
26	login	User admin logged in	2025-11-21 12:06:44.385247	127.0.0.1	1	\N	\N
28	user_registered	PWD registered: 2025-0002 - asd asdasd	2025-11-21 12:58:59.631354	127.0.0.1	1	\N	8
29	profile_updated	PWD updated: 2025-0002 - asd a asdasd	2025-11-21 13:49:56.760177	127.0.0.1	1	\N	8
30	profile_updated	PWD updated: 2025-0002 - asd a asdasd	2025-11-21 13:50:35.235239	127.0.0.1	1	\N	8
31	pwd_archived	PWD archived: 2025-0002 - asd a asdasd	2025-11-21 13:56:57.306047	127.0.0.1	1	\N	8
\.


--
-- TOC entry 5028 (class 0 OID 34624)
-- Dependencies: 237
-- Data for Name: auth_group; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_group (id, name) FROM stdin;
\.


--
-- TOC entry 5030 (class 0 OID 34632)
-- Dependencies: 239
-- Data for Name: auth_group_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_group_permissions (id, group_id, permission_id) FROM stdin;
\.


--
-- TOC entry 5026 (class 0 OID 34618)
-- Dependencies: 235
-- Data for Name: auth_permission; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_permission (id, name, content_type_id, codename) FROM stdin;
1	Can add log entry	1	add_logentry
2	Can change log entry	1	change_logentry
3	Can delete log entry	1	delete_logentry
4	Can view log entry	1	view_logentry
5	Can add permission	2	add_permission
6	Can change permission	2	change_permission
7	Can delete permission	2	delete_permission
8	Can view permission	2	view_permission
9	Can add group	3	add_group
10	Can change group	3	change_group
11	Can delete group	3	delete_group
12	Can view group	3	view_group
13	Can add user	4	add_user
14	Can change user	4	change_user
15	Can delete user	4	delete_user
16	Can view user	4	view_user
17	Can add content type	5	add_contenttype
18	Can change content type	5	change_contenttype
19	Can delete content type	5	delete_contenttype
20	Can view content type	5	view_contenttype
21	Can add session	6	add_session
22	Can change session	6	change_session
23	Can delete session	6	delete_session
24	Can view session	6	view_session
25	Can add user	7	add_user
26	Can change user	7	change_user
27	Can delete user	7	delete_user
28	Can view user	7	view_user
29	Can add audit log	8	add_auditlog
30	Can change audit log	8	change_auditlog
31	Can delete audit log	8	delete_auditlog
32	Can view audit log	8	view_auditlog
33	Can add pwd profile	9	add_pwdprofile
34	Can change pwd profile	9	change_pwdprofile
35	Can delete pwd profile	9	delete_pwdprofile
36	Can view pwd profile	9	view_pwdprofile
37	Can add pwd document	10	add_pwddocument
38	Can change pwd document	10	change_pwddocument
39	Can delete pwd document	10	delete_pwddocument
40	Can view pwd document	10	view_pwddocument
\.


--
-- TOC entry 5032 (class 0 OID 34638)
-- Dependencies: 241
-- Data for Name: auth_user; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) FROM stdin;
\.


--
-- TOC entry 5034 (class 0 OID 34646)
-- Dependencies: 243
-- Data for Name: auth_user_groups; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_user_groups (id, user_id, group_id) FROM stdin;
\.


--
-- TOC entry 5036 (class 0 OID 34652)
-- Dependencies: 245
-- Data for Name: auth_user_user_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.auth_user_user_permissions (id, user_id, permission_id) FROM stdin;
\.


--
-- TOC entry 5038 (class 0 OID 34710)
-- Dependencies: 247
-- Data for Name: django_admin_log; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_admin_log (id, action_time, object_id, object_repr, action_flag, change_message, content_type_id, user_id) FROM stdin;
\.


--
-- TOC entry 5024 (class 0 OID 34610)
-- Dependencies: 233
-- Data for Name: django_content_type; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_content_type (id, app_label, model) FROM stdin;
1	admin	logentry
2	auth	permission
3	auth	group
4	auth	user
5	contenttypes	contenttype
6	sessions	session
7	accounts	user
8	accounts	auditlog
9	pwd	pwdprofile
10	pwd	pwddocument
\.


--
-- TOC entry 5022 (class 0 OID 34602)
-- Dependencies: 231
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_migrations (id, app, name, applied) FROM stdin;
1	accounts	0001_initial	2025-11-21 00:23:39.567852+08
2	contenttypes	0001_initial	2025-11-21 00:29:40.891567+08
3	auth	0001_initial	2025-11-21 00:29:40.984318+08
4	admin	0001_initial	2025-11-21 00:29:41.010249+08
5	admin	0002_logentry_remove_auto_add	2025-11-21 00:29:41.02122+08
6	admin	0003_logentry_add_action_flag_choices	2025-11-21 00:29:41.032221+08
7	contenttypes	0002_remove_content_type_name	2025-11-21 00:29:41.08013+08
8	auth	0002_alter_permission_name_max_length	2025-11-21 00:29:41.090096+08
9	auth	0003_alter_user_email_max_length	2025-11-21 00:29:41.102066+08
10	auth	0004_alter_user_username_opts	2025-11-21 00:29:41.11104+08
11	auth	0005_alter_user_last_login_null	2025-11-21 00:29:41.124006+08
12	auth	0006_require_contenttypes_0002	2025-11-21 00:29:41.133979+08
13	auth	0007_alter_validators_add_error_messages	2025-11-21 00:29:41.143952+08
14	auth	0008_alter_user_username_max_length	2025-11-21 00:29:41.160906+08
15	auth	0009_alter_user_last_name_max_length	2025-11-21 00:29:41.17487+08
16	auth	0010_alter_group_name_max_length	2025-11-21 00:29:41.191824+08
17	auth	0011_update_proxy_permissions	2025-11-21 00:29:41.205787+08
18	auth	0012_alter_user_first_name_max_length	2025-11-21 00:29:41.219749+08
19	sessions	0001_initial	2025-11-21 00:29:41.230187+08
20	accounts	0002_alter_user_verified_by	2025-11-21 15:43:24.981689+08
22	pwd	0001_initial	2025-11-21 20:12:02.146518+08
\.


--
-- TOC entry 5039 (class 0 OID 34738)
-- Dependencies: 248
-- Data for Name: django_session; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.django_session (session_key, session_data, expire_date) FROM stdin;
pmp3r5v7paht378t2v2j5px0bdglxjrq	.eJyrViotTi2Kz0xRsjLUAbPzEnNTlayUElNyM_OUdJSK8nOQuZnF8WWpRZlpmalAHSVFpam1AOLVFoY:1vMPuW:JNC-dJsGM8eO6ZfexrR1qrJUxhdxf5ARvzDZo4ps-WU	2025-12-05 20:06:44.409144+08
\.


--
-- TOC entry 5020 (class 0 OID 34544)
-- Dependencies: 224
-- Data for Name: pwd_documents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.pwd_documents (id, pwd_profile_id, uploaded_by, file_path, file_name, file_type, file_size, uploaded_at) FROM stdin;
\.


--
-- TOC entry 5018 (class 0 OID 34500)
-- Dependencies: 222
-- Data for Name: pwd_profile; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.pwd_profile (id, unique_id, is_active, created_at, updated_at, created_by, updated_by, first_name, middle_name, last_name, suffix, birthdate, sex, religion, barangay, address, contact_number, nationality, civil_status, photo_path, living_situation, guardian_name, guardian_contact, household_income, household_size, housing_type, educational_attainment, employment_status, occupation, type_of_employment, disability_type, cause_of_disability, degree_of_disability, date_diagnosed, assistive_devices, medication, allergies, emergency_contact_name, emergency_contact_number, emergency_contact_address, philhealth_number, sss_gsis_number, skills_hobbies, organization_membership, government_health_benefits, remarks, fingerprint_data) FROM stdin;
7	2025-0001	t	2025-11-21 12:54:12.395636	2025-11-21 12:54:12.395636	1	1	asdasd		asdasdasd		2002-02-22	M	dadasdasd	asdasdasd	asdasdasdas	1231312312	Filipino	Single	\N		asdasdasd	131231231	\N	\N		None	Employed			Visual		Low	\N			\N	asdasdasda	54564564564	adasdasdasdad					\N	\N	\N
8	2025-0002	f	2025-11-21 12:58:59.603459	2025-11-21 13:56:57.274022	1	1	asd	a	asdasd		2002-02-22	M	asdasd	asdasdad	asdasdasdasda	1231231	Filipino	Single	\N		asadsaasd	46456456	\N	\N		None	Employed			Visual		Low	\N			\N	asdasdad	4645645	asdasdasdasd		12312313123			\N	\N	\N
\.


--
-- TOC entry 5014 (class 0 OID 34441)
-- Dependencies: 218
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, username, password, role, is_active, is_verified, created_at, updated_at, verified_at, verified_by, security_question, security_answer, first_name, middle_name, last_name, suffix, birthdate, sex, religion, home_address, contact_number, nationality, civil_status, educational_attainment, employment_status, occupation, emergency_contact_name, emergency_contact_number, emergency_contact_address, valid_id_path) FROM stdin;
1	admin	pbkdf2_sha256$870000$oBdSvjESVN67hr13DOttOL$ig3AFQMXEApAbhgKeMfYWt+VhlQmmCEtn4JT/Od/LyI=	admin	t	t	2025-11-20 15:44:15.052799	2025-11-20 15:44:15.052799	2025-11-20 15:44:15.052799	\N	What is your mother's maiden name?	pbkdf2_sha256$870000$R54iFnjwTcmmsJ8UAUNoXc$AvMIjVHmm9XPqnNlQpw0pLbc1e+eb5cKhGpjodUhDvs=	System	\N	Administrator	\N	1990-01-01	M	N/A	System Office	09171234567	Filipino	Single	College Graduate	Employed	System Administrator	Emergency Contact	09171234567	Emergency Address	admin_id.jpg
2	meow	pbkdf2_sha256$870000$w3YZdzH56J9D3rwFgmittm$wWs0DyMMfP8mVtQSVI6yw9tiDp+6MBCDqG7K9zpIMt4=	basic_user	f	t	2025-11-20 17:14:14.53828	2025-11-21 06:20:12.618609	2025-11-21 14:19:36.478535	1	meow	pbkdf2_sha256$870000$Jwk3eRZpnVHp9TGZNTAGhd$sH2DgSy+Ir7ebePMwev6XbGZANmj4XUIXdsYQ4S++18=	mewo	mewo	mewo		2000-02-22	M	Roman	mewomewo	123123123	Filipino	Single	Elementary	Employed	mewowm	asdasdasd	123123123	adasdawdasdasd	user_ids/meow_validid.png
3	qwe	pbkdf2_sha256$870000$oF2V13vCoEQ9DKGPzF2X34$Uz3QJDkwTNMRuI5XUn/LPW18HMboc/HcH3bTaEPhc4U=	basic_user	t	t	2025-11-21 07:14:15.762806	2025-11-21 07:22:50.163889	2025-11-21 15:17:20.803775	1	meow	pbkdf2_sha256$870000$w2tyMpVMHfE6ejqUOuO2qn$vwA5iaT/aYkSfxbCaK+FtVNrnqh9Lz2KxN+QqO3XY70=	HAHAHAHAHA	qwe	qwe		2000-12-12	M	qwe	qweqweqweqwe	1232341123	Filipino	Single	College	Employed	asd	asd	123123	asdasdadad	user_ids/qwe_validid.png
\.


--
-- TOC entry 5074 (class 0 OID 0)
-- Dependencies: 219
-- Name: audit_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.audit_log_id_seq', 31, true);


--
-- TOC entry 5075 (class 0 OID 0)
-- Dependencies: 236
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_group_id_seq', 1, false);


--
-- TOC entry 5076 (class 0 OID 0)
-- Dependencies: 238
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_group_permissions_id_seq', 1, false);


--
-- TOC entry 5077 (class 0 OID 0)
-- Dependencies: 234
-- Name: auth_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_permission_id_seq', 40, true);


--
-- TOC entry 5078 (class 0 OID 0)
-- Dependencies: 242
-- Name: auth_user_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_user_groups_id_seq', 1, false);


--
-- TOC entry 5079 (class 0 OID 0)
-- Dependencies: 240
-- Name: auth_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_user_id_seq', 1, false);


--
-- TOC entry 5080 (class 0 OID 0)
-- Dependencies: 244
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.auth_user_user_permissions_id_seq', 1, false);


--
-- TOC entry 5081 (class 0 OID 0)
-- Dependencies: 246
-- Name: django_admin_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_admin_log_id_seq', 1, false);


--
-- TOC entry 5082 (class 0 OID 0)
-- Dependencies: 232
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_content_type_id_seq', 10, true);


--
-- TOC entry 5083 (class 0 OID 0)
-- Dependencies: 230
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.django_migrations_id_seq', 22, true);


--
-- TOC entry 5084 (class 0 OID 0)
-- Dependencies: 223
-- Name: pwd_documents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.pwd_documents_id_seq', 1, false);


--
-- TOC entry 5085 (class 0 OID 0)
-- Dependencies: 221
-- Name: pwd_profiles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.pwd_profiles_id_seq', 8, true);


--
-- TOC entry 5086 (class 0 OID 0)
-- Dependencies: 217
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 3, true);


--
-- TOC entry 4769 (class 2606 OID 34483)
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- TOC entry 4810 (class 2606 OID 34736)
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- TOC entry 4815 (class 2606 OID 34667)
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- TOC entry 4818 (class 2606 OID 34636)
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- TOC entry 4812 (class 2606 OID 34628)
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- TOC entry 4805 (class 2606 OID 34658)
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- TOC entry 4807 (class 2606 OID 34622)
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- TOC entry 4826 (class 2606 OID 34650)
-- Name: auth_user_groups auth_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_pkey PRIMARY KEY (id);


--
-- TOC entry 4829 (class 2606 OID 34682)
-- Name: auth_user_groups auth_user_groups_user_id_group_id_94350c0c_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq UNIQUE (user_id, group_id);


--
-- TOC entry 4820 (class 2606 OID 34642)
-- Name: auth_user auth_user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);


--
-- TOC entry 4832 (class 2606 OID 34656)
-- Name: auth_user_user_permissions auth_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_pkey PRIMARY KEY (id);


--
-- TOC entry 4835 (class 2606 OID 34696)
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_permission_id_14a6b632_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq UNIQUE (user_id, permission_id);


--
-- TOC entry 4823 (class 2606 OID 34731)
-- Name: auth_user auth_user_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_username_key UNIQUE (username);


--
-- TOC entry 4838 (class 2606 OID 34717)
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- TOC entry 4800 (class 2606 OID 34616)
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- TOC entry 4802 (class 2606 OID 34614)
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- TOC entry 4798 (class 2606 OID 34608)
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- TOC entry 4842 (class 2606 OID 34744)
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- TOC entry 4796 (class 2606 OID 34554)
-- Name: pwd_documents pwd_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pwd_documents
    ADD CONSTRAINT pwd_documents_pkey PRIMARY KEY (id);


--
-- TOC entry 4789 (class 2606 OID 34517)
-- Name: pwd_profile pwd_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pwd_profile
    ADD CONSTRAINT pwd_profiles_pkey PRIMARY KEY (id);


--
-- TOC entry 4791 (class 2606 OID 34519)
-- Name: pwd_profile pwd_profiles_unique_pwd_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pwd_profile
    ADD CONSTRAINT pwd_profiles_unique_pwd_id_key UNIQUE (unique_id);


--
-- TOC entry 4765 (class 2606 OID 34459)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 4767 (class 2606 OID 34461)
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- TOC entry 4808 (class 1259 OID 34737)
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- TOC entry 4813 (class 1259 OID 34678)
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- TOC entry 4816 (class 1259 OID 34679)
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- TOC entry 4803 (class 1259 OID 34664)
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- TOC entry 4824 (class 1259 OID 34694)
-- Name: auth_user_groups_group_id_97559544; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_user_groups_group_id_97559544 ON public.auth_user_groups USING btree (group_id);


--
-- TOC entry 4827 (class 1259 OID 34693)
-- Name: auth_user_groups_user_id_6a12ed8b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_user_groups_user_id_6a12ed8b ON public.auth_user_groups USING btree (user_id);


--
-- TOC entry 4830 (class 1259 OID 34708)
-- Name: auth_user_user_permissions_permission_id_1fbb5f2c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON public.auth_user_user_permissions USING btree (permission_id);


--
-- TOC entry 4833 (class 1259 OID 34707)
-- Name: auth_user_user_permissions_user_id_a95ead1b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON public.auth_user_user_permissions USING btree (user_id);


--
-- TOC entry 4821 (class 1259 OID 34732)
-- Name: auth_user_username_6821ab7c_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX auth_user_username_6821ab7c_like ON public.auth_user USING btree (username varchar_pattern_ops);


--
-- TOC entry 4836 (class 1259 OID 34728)
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- TOC entry 4839 (class 1259 OID 34729)
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- TOC entry 4840 (class 1259 OID 34746)
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- TOC entry 4843 (class 1259 OID 34745)
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- TOC entry 4770 (class 1259 OID 34494)
-- Name: idx_audit_action_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_action_type ON public.audit_log USING btree (action_type);


--
-- TOC entry 4771 (class 1259 OID 34498)
-- Name: idx_audit_target_pwd; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_target_pwd ON public.audit_log USING btree (target_pwd_id);


--
-- TOC entry 4772 (class 1259 OID 34497)
-- Name: idx_audit_target_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_target_user ON public.audit_log USING btree (target_user_id);


--
-- TOC entry 4773 (class 1259 OID 34495)
-- Name: idx_audit_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_timestamp ON public.audit_log USING btree ("timestamp" DESC);


--
-- TOC entry 4774 (class 1259 OID 34496)
-- Name: idx_audit_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_user_id ON public.audit_log USING btree (user_id);


--
-- TOC entry 4792 (class 1259 OID 34565)
-- Name: idx_docs_pwd_profile; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_docs_pwd_profile ON public.pwd_documents USING btree (pwd_profile_id);


--
-- TOC entry 4793 (class 1259 OID 34567)
-- Name: idx_docs_uploaded_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_docs_uploaded_at ON public.pwd_documents USING btree (uploaded_at DESC);


--
-- TOC entry 4794 (class 1259 OID 34566)
-- Name: idx_docs_uploaded_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_docs_uploaded_by ON public.pwd_documents USING btree (uploaded_by);


--
-- TOC entry 4775 (class 1259 OID 34538)
-- Name: idx_pwd_barangay; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_pwd_barangay ON public.pwd_profile USING btree (barangay);


--
-- TOC entry 4776 (class 1259 OID 34536)
-- Name: idx_pwd_birthdate; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_pwd_birthdate ON public.pwd_profile USING btree (birthdate);


--
-- TOC entry 4777 (class 1259 OID 34541)
-- Name: idx_pwd_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_pwd_created_at ON public.pwd_profile USING btree (created_at DESC);


--
-- TOC entry 4778 (class 1259 OID 34534)
-- Name: idx_pwd_created_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_pwd_created_by ON public.pwd_profile USING btree (created_by);


--
-- TOC entry 4779 (class 1259 OID 34539)
-- Name: idx_pwd_degree; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_pwd_degree ON public.pwd_profile USING btree (degree_of_disability);


--
-- TOC entry 4780 (class 1259 OID 34540)
-- Name: idx_pwd_employment; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_pwd_employment ON public.pwd_profile USING btree (employment_status);


--
-- TOC entry 4781 (class 1259 OID 34532)
-- Name: idx_pwd_first_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_pwd_first_name ON public.pwd_profile USING btree (first_name);


--
-- TOC entry 4782 (class 1259 OID 34542)
-- Name: idx_pwd_fullname; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_pwd_fullname ON public.pwd_profile USING gin (to_tsvector('english'::regconfig, (((((first_name)::text || ' '::text) || (COALESCE(middle_name, ''::character varying))::text) || ' '::text) || (last_name)::text)));


--
-- TOC entry 4783 (class 1259 OID 34533)
-- Name: idx_pwd_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_pwd_is_active ON public.pwd_profile USING btree (is_active);


--
-- TOC entry 4784 (class 1259 OID 34531)
-- Name: idx_pwd_last_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_pwd_last_name ON public.pwd_profile USING btree (last_name);


--
-- TOC entry 4785 (class 1259 OID 34537)
-- Name: idx_pwd_sex; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_pwd_sex ON public.pwd_profile USING btree (sex);


--
-- TOC entry 4786 (class 1259 OID 34530)
-- Name: idx_pwd_unique_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_pwd_unique_id ON public.pwd_profile USING btree (unique_id);


--
-- TOC entry 4787 (class 1259 OID 34535)
-- Name: idx_pwd_updated_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_pwd_updated_by ON public.pwd_profile USING btree (updated_by);


--
-- TOC entry 4758 (class 1259 OID 34472)
-- Name: idx_users_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_created_at ON public.users USING btree (created_at);


--
-- TOC entry 4759 (class 1259 OID 34469)
-- Name: idx_users_is_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_is_active ON public.users USING btree (is_active);


--
-- TOC entry 4760 (class 1259 OID 34470)
-- Name: idx_users_is_verified; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_is_verified ON public.users USING btree (is_verified);


--
-- TOC entry 4761 (class 1259 OID 34471)
-- Name: idx_users_last_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_last_name ON public.users USING btree (last_name);


--
-- TOC entry 4762 (class 1259 OID 34468)
-- Name: idx_users_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_role ON public.users USING btree (role);


--
-- TOC entry 4763 (class 1259 OID 34467)
-- Name: idx_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_username ON public.users USING btree (username);


--
-- TOC entry 4862 (class 2620 OID 34575)
-- Name: pwd_profile trigger_pwd_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_pwd_updated_at BEFORE UPDATE ON public.pwd_profile FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 4861 (class 2620 OID 34574)
-- Name: users trigger_users_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trigger_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 4853 (class 2606 OID 34673)
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4854 (class 2606 OID 34668)
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4852 (class 2606 OID 34659)
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4855 (class 2606 OID 34688)
-- Name: auth_user_groups auth_user_groups_group_id_97559544_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4856 (class 2606 OID 34683)
-- Name: auth_user_groups auth_user_groups_user_id_6a12ed8b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4857 (class 2606 OID 34702)
-- Name: auth_user_user_permissions auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4858 (class 2606 OID 34697)
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4859 (class 2606 OID 34718)
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4860 (class 2606 OID 34723)
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- TOC entry 4845 (class 2606 OID 34568)
-- Name: audit_log fk_audit_target_pwd; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT fk_audit_target_pwd FOREIGN KEY (target_pwd_id) REFERENCES public.pwd_profile(id) ON DELETE SET NULL;


--
-- TOC entry 4846 (class 2606 OID 34489)
-- Name: audit_log fk_audit_target_user; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT fk_audit_target_user FOREIGN KEY (target_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 4847 (class 2606 OID 34484)
-- Name: audit_log fk_audit_user; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 4850 (class 2606 OID 34555)
-- Name: pwd_documents fk_doc_pwd_profile; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pwd_documents
    ADD CONSTRAINT fk_doc_pwd_profile FOREIGN KEY (pwd_profile_id) REFERENCES public.pwd_profile(id) ON DELETE CASCADE;


--
-- TOC entry 4851 (class 2606 OID 34560)
-- Name: pwd_documents fk_doc_uploaded_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pwd_documents
    ADD CONSTRAINT fk_doc_uploaded_by FOREIGN KEY (uploaded_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 4848 (class 2606 OID 34520)
-- Name: pwd_profile fk_pwd_created_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pwd_profile
    ADD CONSTRAINT fk_pwd_created_by FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- TOC entry 4849 (class 2606 OID 34525)
-- Name: pwd_profile fk_pwd_updated_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pwd_profile
    ADD CONSTRAINT fk_pwd_updated_by FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 4844 (class 2606 OID 34748)
-- Name: users users_verified_by_da7a0e0e_fk_users_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_verified_by_da7a0e0e_fk_users_id FOREIGN KEY (verified_by) REFERENCES public.users(id) DEFERRABLE INITIALLY DEFERRED;


-- Completed on 2025-11-22 00:18:43

--
-- PostgreSQL database dump complete
--

